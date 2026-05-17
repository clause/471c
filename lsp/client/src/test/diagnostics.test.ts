/* --------------------------------------------------------------------------------------------
 * Copyright (c) Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. See License.txt in the project root for license information.
 * ------------------------------------------------------------------------------------------ */

import * as vscode from 'vscode';
import * as assert from 'assert';
import { getDocUri, activate } from './helper';

suite('Should get diagnostics', () => {
	const docUri = getDocUri('diagnostics.l3');
	const l4DocUri = getDocUri('diagnostics.l4');

	test('Diagnoses unbound variables', async () => {
		await testDiagnostics(docUri, [
			{ message: 'Unbound variable: x', range: toRange(0, 7, 0, 8), severity: vscode.DiagnosticSeverity.Error, source: 'l3' }
		]);
	});

	test('Diagnoses malformed L4 syntax', async () => {
		await activate(l4DocUri);

		const actualDiagnostics = vscode.languages.getDiagnostics(l4DocUri);

		assert.ok(actualDiagnostics.length > 0);
		assert.equal(actualDiagnostics[0].severity, vscode.DiagnosticSeverity.Error);
		assert.equal(actualDiagnostics[0].source, 'l4');
		assert.equal(actualDiagnostics[0].message, 'Missing closing parenthesis.');
	});
});

function toRange(sLine: number, sChar: number, eLine: number, eChar: number) {
	const start = new vscode.Position(sLine, sChar);
	const end = new vscode.Position(eLine, eChar);
	return new vscode.Range(start, end);
}

async function testDiagnostics(docUri: vscode.Uri, expectedDiagnostics: vscode.Diagnostic[]) {
	await activate(docUri);

	const actualDiagnostics = vscode.languages.getDiagnostics(docUri);

	assert.equal(actualDiagnostics.length, expectedDiagnostics.length);

	expectedDiagnostics.forEach((expectedDiagnostic, i) => {
		const actualDiagnostic = actualDiagnostics[i];
		assert.equal(actualDiagnostic.message, expectedDiagnostic.message);
		assert.deepEqual(actualDiagnostic.range, expectedDiagnostic.range);
		assert.equal(actualDiagnostic.severity, expectedDiagnostic.severity);
	});
}