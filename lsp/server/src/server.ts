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
	SemanticTokensBuilder,
	SemanticTokensRequest
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
const repositoryRootPath = dirname(dirname(dirname(__dirname)));

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

	connection.console.log('[Initialize] Server initializing');
	connection.console.log(`[Initialize] Client supports textDocument.semanticTokens: ${!!capabilities.textDocument?.semanticTokens}`);

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
			// Semantic tokens for simple keyword/type highlighting in .l4 files
			semanticTokensProvider: {
				legend: {
					tokenTypes: ['keyword', 'type'],
					tokenModifiers: []
				},
					full: true
			}
		}
	};
	
	connection.console.log('[Initialize] Advertising semanticTokensProvider capability');

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
	connection.console.log('[Initialized] Server initialized');
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
			(change.settings['471cLSP'] || defaultSettings)
		);
	}
});

function getDocumentSettings(resource: string): Thenable<ExampleSettings> {
	if (!hasConfigurationCapability) {
		return Promise.resolve(globalSettings);
	}
	let result = documentSettings.get(resource);
	if (!result) {
		result = connection.workspace.getConfiguration({
			scopeUri: resource,
			section: '471cLSP'
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

// The content of a text document has changed. This event is emitted
// when the text document first opened or when its content has changed.
documents.onDidChangeContent(change => {
	void publishDiagnostics(change.document);
});

documents.onDidOpen(event => {
	connection.console.log(`[DocumentOpen] Opened: ${event.document.uri}, languageId: ${event.document.languageId}`);
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

// Allow mapping diagnostics for multiple languages (L3/L4)
function toLspDiagnosticFor(uri: string, diagnostic: L3Diagnostic, source: string): Diagnostic {
	const d = toLspDiagnostic(uri, diagnostic);
	d.source = source;
	return d;
}

function toL4SyntaxDiagnostic(uri: string, text: string): Diagnostic | null {
	const stack: Array<{ line: number; character: number }> = [];
	const lines = text.split(/\r?\n/);

	for (let lineIndex = 0; lineIndex < lines.length; lineIndex++) {
		const line = lines[lineIndex];
		for (let character = 0; character < line.length; character++) {
			const ch = line[character];
			if (ch === '(') {
				stack.push({ line: lineIndex, character });
			} else if (ch === ')') {
				if (stack.length === 0) {
					return {
						severity: DiagnosticSeverity.Error,
						range: {
							start: { line: lineIndex, character },
							end: { line: lineIndex, character: character + 1 }
						},
						message: 'Unmatched closing parenthesis.',
						source: 'l4',
						code: 'L4_SYNTAX_ERROR'
					};
				}
				stack.pop();
			}
		}
	}

	if (stack.length === 0) {
		return null;
	}

	const lastLineIndex = lines.length - 1;
	const lastCharacter = lines[lastLineIndex]?.length ?? 0;
	return {
		severity: DiagnosticSeverity.Error,
		range: {
			start: { line: lastLineIndex, character: lastCharacter },
			end: { line: lastLineIndex, character: lastCharacter + 1 }
		},
		message: 'Missing closing parenthesis.',
		source: 'l4',
		code: 'L4_SYNTAX_ERROR'
	};
}

async function createTempL3File(text: string): Promise<{ dirPath: string; filePath: string }> {
	const dirPath = await mkdtemp(join(tmpdir(), 'l3-lsp-'));
	const filePath = join(dirPath, 'document.l3');
	await writeFile(filePath, text, 'utf8');
	return { dirPath, filePath };
}

async function runL3Diagnostics(filePath: string): Promise<L3DiagnosticsReport> {
	const projectRootCandidates = [workspaceRootPath, repositoryRootPath].filter((candidate): candidate is string => {
		return typeof candidate === 'string' && existsSync(join(candidate, 'packages', 'L3'));
	});
	const workingDirectory = projectRootCandidates[0] ?? workspaceRootPath ?? dirname(filePath);
	const commandCandidates: Array<{ command: string; args: string[] }> = [];

	for (const rootPath of projectRootCandidates) {
		const venvL3 = join(rootPath, '.venv', 'bin', 'l3');
		if (existsSync(venvL3)) {
			commandCandidates.push({ command: venvL3, args: ['--diagnostics-json', filePath] });
		}

		const venvPython = join(rootPath, '.venv', 'bin', 'python');
		if (existsSync(venvPython)) {
			commandCandidates.push({ command: venvPython, args: ['-m', 'L3.main', '--diagnostics-json', filePath] });
		}
	}

	commandCandidates.push({ command: 'l3', args: ['--diagnostics-json', filePath] });
	commandCandidates.push({ command: 'python3', args: ['-m', 'L3.main', '--diagnostics-json', filePath] });

	let lastError = '';

	// Build a PYTHONPATH from several candidate roots so `-m L4.main` can import local package sources.
	const rootCandidates = new Set<string | undefined>(projectRootCandidates);
	if (repositoryRootPath) rootCandidates.add(repositoryRootPath);
	if (workspaceRootPath) rootCandidates.add(workspaceRootPath);
	rootCandidates.add(process.cwd());

	const pyPathEntries: string[] = [];
	for (const root of rootCandidates) {
		if (!root) continue;
		pyPathEntries.push(join(root, 'packages', 'L4', 'src'));
		pyPathEntries.push(join(root, 'packages', 'L3', 'src'));
		pyPathEntries.push(join(root, 'packages', 'L2', 'src'));
		pyPathEntries.push(join(root, 'packages', 'util', 'src'));
	}

	// Keep only unique and existing paths (but allow non-existing to avoid being too strict)
	const unique = Array.from(new Set(pyPathEntries));
	const env = { ...(process.env as NodeJS.ProcessEnv) };
	env.PYTHONPATH = unique.join(':');

	for (const candidate of commandCandidates) {
		try {
			const result = await execFileAsync(candidate.command, candidate.args, { cwd: workingDirectory, env });
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

async function createTempL4File(text: string): Promise<{ dirPath: string; filePath: string }> {
	const dirPath = await mkdtemp(join(tmpdir(), 'l4-lsp-'));
	const filePath = join(dirPath, 'document.l4');
 	await writeFile(filePath, text, 'utf8');
 	return { dirPath, filePath };
}

async function runL4Diagnostics(filePath: string): Promise<L3DiagnosticsReport> {
	const projectRootCandidates = [workspaceRootPath, repositoryRootPath].filter((candidate): candidate is string => {
		return typeof candidate === 'string' && existsSync(join(candidate, 'packages', 'L4'));
	});
	const workingDirectory = projectRootCandidates[0] ?? workspaceRootPath ?? dirname(filePath);
	const commandCandidates: Array<{ command: string; args: string[] }> = [];

	for (const rootPath of projectRootCandidates) {
		const venvL4 = join(rootPath, '.venv', 'bin', 'l4');
		if (existsSync(venvL4)) {
			commandCandidates.push({ command: venvL4, args: ['--diagnostics-json', filePath] });
		}

		const venvPython = join(rootPath, '.venv', 'bin', 'python');
		if (existsSync(venvPython)) {
			commandCandidates.push({ command: venvPython, args: ['-m', 'L4.main', '--diagnostics-json', filePath] });
		}
	}

	commandCandidates.push({ command: 'l4', args: ['--diagnostics-json', filePath] });
	commandCandidates.push({ command: 'python3', args: ['-m', 'L4.main', '--diagnostics-json', filePath] });

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
				code: 'L4_DIAGNOSTICS_UNAVAILABLE',
				message: lastError || 'Could not execute L4 diagnostics command.'
			}
		]
	};
}

async function validateTextDocument(textDocument: TextDocument): Promise<Diagnostic[]> {
	// Get settings for every validate run (used for both L3 and L4)
	const settings = await getDocumentSettings(textDocument.uri);

	if (textDocument.uri.endsWith('.l4')) {
		// Publish a quick syntax-only diagnostic immediately for fast feedback.
		const quick = toL4SyntaxDiagnostic(textDocument.uri, textDocument.getText());

		// Asynchronously run the L4 diagnostics CLI and replace diagnostics when it returns.
		(async () => {
			let tempDirPath: string | undefined;
			try {
				toFilePath(textDocument.uri);
				const temp = await createTempL4File(textDocument.getText());
				tempDirPath = temp.dirPath;

				const report = await runL4Diagnostics(temp.filePath);
				let diags: Diagnostic[];
				if (!report.ok) {
					// If CLI unavailable, prefer quick syntax diagnostic if present
					const syntaxDiagnostic = toL4SyntaxDiagnostic(textDocument.uri, textDocument.getText());
					diags = syntaxDiagnostic ? [syntaxDiagnostic] : report.diagnostics
						.slice(0, settings.maxNumberOfProblems)
						.map(diagnostic => toLspDiagnosticFor(textDocument.uri, diagnostic, 'l4'));
				} else {
					diags = report.diagnostics
						.slice(0, settings.maxNumberOfProblems)
						.map(diagnostic => toLspDiagnosticFor(textDocument.uri, diagnostic, 'l4'));
				}

				connection.sendDiagnostics({ uri: textDocument.uri, diagnostics: diags });
			} catch (error) {
				// If running the CLI fails, keep the quick syntax diagnostic (no-op)
				connection.console.log(`[L4 Diagnostics] error: ${error instanceof Error ? error.message : String(error)}`);
			} finally {
				if (tempDirPath) {
					await rm(tempDirPath, { recursive: true, force: true });
				}
			}
		})();

		return quick ? [quick] : [];
	}

	if (!textDocument.uri.endsWith('.l3')) {
		return [];
	}

	// In this example we get the settings for every validate run.
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

	// Semantic tokens: simple keyword/type highlighting for .l4 files
// Semantic tokens: simple keyword/type highlighting for .l4 files
connection.onRequest(SemanticTokensRequest.type, params => {
	const uri = params.textDocument.uri;
	const doc = documents.get(uri);
	connection.console.log(`[SemanticTokens] Received request for uri=${uri}`);
	connection.console.log(`[SemanticTokens] Document exists: ${!!doc}, ends with .l4: ${uri.endsWith('.l4')}`);
	
	if (!uri.endsWith('.l4') || !doc) {
		connection.console.log(`[SemanticTokens] Skipping - not .l4 or no document`);
		return { data: [] };
	}

	// Keywords and types derived from packages/L4/src/L4/L4.lark
	const typeKeywords = ['Int', 'Bool', 'Trivial', 'Product'];
	const syntaxKeywords = [
		'l4', 'let', 'letrec', 'lambda', 'if', 'allocate', 'load', 'store', 'begin',
		'and', 'sole', 'tuple', 'tuple-get', 'join', 'project'
	];

	const all = [...typeKeywords, ...syntaxKeywords];
	// Build a regex that matches whole words; escape names just in case.
	const escaped = all.map(s => s.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&'));
	const regex = new RegExp(`\\b(?:${escaped.join('|')})\\b`, 'g');

	const builder = new SemanticTokensBuilder();
	const lines = doc.getText().split(/\r?\n/);
	connection.console.log(`[SemanticTokens] Processing ${lines.length} lines from document`);
	
	for (let line = 0; line < lines.length; line++) {
		const text = lines[line];
		let match: RegExpExecArray | null;
		regex.lastIndex = 0;
		while ((match = regex.exec(text)) !== null) {
			const word = match[0];
			const startChar = match.index;
			const length = word.length;
			const tokenType = typeKeywords.includes(word) ? 1 /* 'type' */ : 0 /* 'keyword' */;
			connection.console.log(`[SemanticTokens] Token: "${word}" at ${line}:${startChar}, type=${tokenType}`);
			builder.push(line, startChar, length, tokenType, 0);
		}
	}

	const result = builder.build();
	connection.console.log(`[SemanticTokens] Returning ${result.data.length} data elements`);
	return result;
});

// Make the text document manager listen on the connection
// for open, change and close text document events
documents.listen(connection);

// Listen on the connection
connection.listen();
