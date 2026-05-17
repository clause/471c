import * as assert from 'assert';
import * as vscode from 'vscode';
import { activate, getDocUri } from './helper';

suite('Should provide semantic tokens', () => {
	const docUri = getDocUri('highlighting.l4');

	test('Highlights L4 keywords and types', async () => {
		await activate(docUri);

		const tokens = (await vscode.commands.executeCommand(
				'vscode.provideDocumentSemanticTokens',
			docUri
		)) as vscode.SemanticTokens | undefined;

		assert.ok(tokens);
		assert.ok(tokens.data.length > 0);
	});
});