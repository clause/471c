import {
	createConnection,
	TextDocuments,
	Diagnostic,
	DiagnosticSeverity,
	ProposedFeatures,
	InitializeParams,
	DidChangeConfigurationNotification,
	CompletionItem,
	CompletionItemKind,
	TextDocumentPositionParams,
	TextDocumentSyncKind,
	InitializeResult,
	DocumentDiagnosticReportKind,
	type DocumentDiagnosticReport
} from 'vscode-languageserver/node';
import { execFile } from 'node:child_process';
import { existsSync } from 'node:fs';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

import {
	TextDocument
} from 'vscode-languageserver-textdocument';

const execFileAsync = promisify(execFile);

// Create a connection for the server, using Node's IPC as a transport.
// Also include all preview / proposed LSP features.
const connection = createConnection(ProposedFeatures.all);

// Create a simple text document manager.
const documents = new TextDocuments(TextDocument);

let hasConfigurationCapability = false;
let hasWorkspaceFolderCapability = false;
let hasDiagnosticRelatedInformationCapability = false;
let workspaceRootPath: string | undefined;

interface L3Diagnostic {
	stage: 'syntax' | 'semantic' | 'internal';
	severity: 'error' | 'warning' | 'information';
	code: string;
	message: string;
	line?: number;
	column?: number;
	end_line?: number;
	end_column?: number;
	snippet?: string;
}

interface L3DiagnosticsReport {
	ok: boolean;
	diagnostics: L3Diagnostic[];
}

interface ExecFailure {
	code?: string | number;
	stdout?: string;
	stderr?: string;
}

connection.onInitialize((params: InitializeParams) => {
	const capabilities = params.capabilities;
	workspaceRootPath = extractWorkspaceRootPath(params);

	// Does the client support the `workspace/configuration` request?
	// If not, we fall back using global settings.
	hasConfigurationCapability = !!(
		capabilities.workspace && !!capabilities.workspace.configuration
	);
	hasWorkspaceFolderCapability = !!(
		capabilities.workspace && !!capabilities.workspace.workspaceFolders
	);
	hasDiagnosticRelatedInformationCapability = !!(
		capabilities.textDocument &&
		capabilities.textDocument.publishDiagnostics &&
		capabilities.textDocument.publishDiagnostics.relatedInformation
	);

	const result: InitializeResult = {
		capabilities: {
			textDocumentSync: TextDocumentSyncKind.Incremental,
			// Tell the client that this server supports code completion.
			completionProvider: {
				resolveProvider: true
			},
			diagnosticProvider: {
				interFileDependencies: false,
				workspaceDiagnostics: false
			}
		}
	};
	if (hasWorkspaceFolderCapability) {
		result.capabilities.workspace = {
			workspaceFolders: {
				supported: true
			}
		};
	}
	return result;
});

connection.onInitialized(() => {
	if (hasConfigurationCapability) {
		// Register for all configuration changes.
		connection.client.register(DidChangeConfigurationNotification.type, undefined);
	}
	if (hasWorkspaceFolderCapability) {
		connection.workspace.onDidChangeWorkspaceFolders(_event => {
			connection.console.log('Workspace folder change event received.');
		});
	}
});

// The example settings
interface ExampleSettings {
	maxNumberOfProblems: number;
}

// The global settings, used when the `workspace/configuration` request is not supported by the client.
// Please note that this is not the case when using this server with the client provided in this example
// but could happen with other clients.
const defaultSettings: ExampleSettings = { maxNumberOfProblems: 1000 };
let globalSettings: ExampleSettings = defaultSettings;

// Cache the settings of all open documents
const documentSettings = new Map<string, Thenable<ExampleSettings>>();

connection.onDidChangeConfiguration(change => {
	if (hasConfigurationCapability) {
		// Reset all cached document settings
		documentSettings.clear();
	} else {
		globalSettings = (
			(change.settings.languageServerExample || defaultSettings)
		);
	}
	// Refresh the diagnostics since the `maxNumberOfProblems` could have changed.
	// We could optimize things here and re-fetch the setting first can compare it
	// to the existing setting, but this is out of scope for this example.
	connection.languages.diagnostics.refresh();
});

function getDocumentSettings(resource: string): Thenable<ExampleSettings> {
	if (!hasConfigurationCapability) {
		return Promise.resolve(globalSettings);
	}
	let result = documentSettings.get(resource);
	if (!result) {
		result = connection.workspace.getConfiguration({
			scopeUri: resource,
			section: 'languageServerExample'
		});
		documentSettings.set(resource, result);
	}
	return result;
}

// Only keep settings for open documents
documents.onDidClose(e => {
	documentSettings.delete(e.document.uri);
	connection.sendDiagnostics({ uri: e.document.uri, diagnostics: [] });
});


connection.languages.diagnostics.on(async (params) => {
	const document = documents.get(params.textDocument.uri);
	if (document !== undefined) {
		return {
			kind: DocumentDiagnosticReportKind.Full,
			items: await validateTextDocument(document)
		} satisfies DocumentDiagnosticReport;
	} else {
		// We don't know the document. We can either try to read it from disk
		// or we don't report problems for it.
		return {
			kind: DocumentDiagnosticReportKind.Full,
			items: []
		} satisfies DocumentDiagnosticReport;
	}
});

// The content of a text document has changed. This event is emitted
// when the text document first opened or when its content has changed.
documents.onDidChangeContent(change => {
	void publishDiagnostics(change.document);
});

documents.onDidOpen(event => {
	void publishDiagnostics(event.document);
});

async function publishDiagnostics(textDocument: TextDocument): Promise<void> {
	const diagnostics = await validateTextDocument(textDocument);
	connection.sendDiagnostics({ uri: textDocument.uri, diagnostics });
}

function extractWorkspaceRootPath(params: InitializeParams): string | undefined {
	const workspaceFolderUri = params.workspaceFolders && params.workspaceFolders.length > 0
		? params.workspaceFolders[0].uri
		: undefined;
	const rootUri = workspaceFolderUri ?? params.rootUri ?? undefined;
	if (!rootUri || !rootUri.startsWith('file://')) {
		return undefined;
	}

	try {
		return fileURLToPath(rootUri);
	} catch {
		return undefined;
	}
}

function toFilePath(uri: string): string {
	if (!uri.startsWith('file://')) {
		throw new Error(`Unsupported URI scheme: ${uri}`);
	}
	return fileURLToPath(uri);
}

function toSeverity(severity: L3Diagnostic['severity']): DiagnosticSeverity {
	switch (severity) {
		case 'warning':
			return DiagnosticSeverity.Warning;
		case 'information':
			return DiagnosticSeverity.Information;
		default:
			return DiagnosticSeverity.Error;
	}
}

function toPosition(value: number | undefined): number {
	if (typeof value !== 'number' || Number.isNaN(value)) {
		return 0;
	}
	return Math.max(0, value - 1);
}

function toLspDiagnostic(uri: string, diagnostic: L3Diagnostic): Diagnostic {
	const startLine = toPosition(diagnostic.line);
	const startCharacter = toPosition(diagnostic.column);
	const endLine = typeof diagnostic.end_line === 'number' ? toPosition(diagnostic.end_line) : startLine;
	const endCharacter = typeof diagnostic.end_column === 'number'
		? toPosition(diagnostic.end_column)
		: startCharacter + 1;

	const lspDiagnostic: Diagnostic = {
		severity: toSeverity(diagnostic.severity),
		range: {
			start: { line: startLine, character: startCharacter },
			end: { line: endLine, character: Math.max(endCharacter, startCharacter + 1) }
		},
		message: diagnostic.message,
		source: 'l3',
		code: diagnostic.code
	};

	if (hasDiagnosticRelatedInformationCapability && diagnostic.snippet) {
		lspDiagnostic.relatedInformation = [
			{
				location: {
					uri,
					range: lspDiagnostic.range
				},
				message: `Source: ${diagnostic.snippet}`
			}
		];
	}

	return lspDiagnostic;
}

async function createTempL3File(text: string): Promise<{ dirPath: string; filePath: string }> {
	const dirPath = await mkdtemp(join(tmpdir(), 'l3-lsp-'));
	const filePath = join(dirPath, 'document.l3');
	await writeFile(filePath, text, 'utf8');
	return { dirPath, filePath };
}

async function runL3Diagnostics(filePath: string): Promise<L3DiagnosticsReport> {
	const workingDirectory = workspaceRootPath ?? dirname(filePath);
	const commandCandidates: Array<{ command: string; args: string[] }> = [];

	if (workspaceRootPath) {
		const venvL3 = join(workspaceRootPath, '.venv', 'bin', 'l3');
		if (existsSync(venvL3)) {
			commandCandidates.push({ command: venvL3, args: ['--diagnostics-json', filePath] });
		}

		const venvPython = join(workspaceRootPath, '.venv', 'bin', 'python');
		if (existsSync(venvPython)) {
			commandCandidates.push({ command: venvPython, args: ['-m', 'L3.main', '--diagnostics-json', filePath] });
		}
	}

	commandCandidates.push({ command: 'l3', args: ['--diagnostics-json', filePath] });
	commandCandidates.push({ command: 'python3', args: ['-m', 'L3.main', '--diagnostics-json', filePath] });

	let lastError = '';

	for (const candidate of commandCandidates) {
		try {
			const result = await execFileAsync(candidate.command, candidate.args, { cwd: workingDirectory });
			const parsed = JSON.parse(result.stdout) as L3DiagnosticsReport;
			if (Array.isArray(parsed.diagnostics)) {
				return parsed;
			}
			lastError = `Invalid diagnostics JSON from ${candidate.command}`;
		} catch (error) {
			const failure = error as ExecFailure;
			if (failure.code === 'ENOENT') {
				continue;
			}

			const stdout = typeof failure.stdout === 'string' ? failure.stdout : '';
			if (stdout.trim().length > 0) {
				try {
					const parsed = JSON.parse(stdout) as L3DiagnosticsReport;
					if (Array.isArray(parsed.diagnostics)) {
						return parsed;
					}
					lastError = `Invalid diagnostics JSON from ${candidate.command}`;
					continue;
				} catch {
					lastError = stdout.trim();
					continue;
				}
			}

			lastError = typeof failure.stderr === 'string' && failure.stderr.trim().length > 0
				? failure.stderr.trim()
				: `Failed to run ${candidate.command}`;
		}
	}

	return {
		ok: false,
		diagnostics: [
			{
				stage: 'internal',
				severity: 'error',
				code: 'L3_DIAGNOSTICS_UNAVAILABLE',
				message: lastError || 'Could not execute L3 diagnostics command.'
			}
		]
	};
}

async function validateTextDocument(textDocument: TextDocument): Promise<Diagnostic[]> {
	if (!textDocument.uri.endsWith('.l3')) {
		return [];
	}

	// In this example we get the settings for every validate run.
	const settings = await getDocumentSettings(textDocument.uri);

	let tempDirPath: string | undefined;
	try {
		toFilePath(textDocument.uri);
		const temp = await createTempL3File(textDocument.getText());
		tempDirPath = temp.dirPath;

		const report = await runL3Diagnostics(temp.filePath);
		return report.diagnostics
			.slice(0, settings.maxNumberOfProblems)
			.map(diagnostic => toLspDiagnostic(textDocument.uri, diagnostic));
	} catch (error) {
		const message = error instanceof Error ? error.message : 'Unknown diagnostics error';
		return [
			{
				severity: DiagnosticSeverity.Error,
				range: {
					start: { line: 0, character: 0 },
					end: { line: 0, character: 1 }
				},
				message,
				source: 'l3',
				code: 'L3_DIAGNOSTICS_RUNTIME_ERROR'
			}
		];
	} finally {
		if (tempDirPath) {
			await rm(tempDirPath, { recursive: true, force: true });
		}
	}
}

connection.onDidChangeWatchedFiles(_change => {
	// Monitored files have change in VSCode
	connection.console.log('We received a file change event');
});

// This handler provides the initial list of the completion items.
connection.onCompletion(
	(_textDocumentPosition: TextDocumentPositionParams): CompletionItem[] => {
		// The pass parameter contains the position of the text document in
		// which code complete got requested. For the example we ignore this
		// info and always provide the same completion items.
		return [
			{
				label: 'TypeScript',
				kind: CompletionItemKind.Text,
				data: 1
			},
			{
				label: 'JavaScript',
				kind: CompletionItemKind.Text,
				data: 2
			}
		];
	}
);

// This handler resolves additional information for the item selected in
// the completion list.
connection.onCompletionResolve(
	(item: CompletionItem): CompletionItem => {
		if (item.data === 1) {
			item.detail = 'TypeScript details';
			item.documentation = 'TypeScript documentation';
		} else if (item.data === 2) {
			item.detail = 'JavaScript details';
			item.documentation = 'JavaScript documentation';
		}
		return item;
	}
);

// Make the text document manager listen on the connection
// for open, change and close text document events
documents.listen(connection);

// Listen on the connection
connection.listen();
