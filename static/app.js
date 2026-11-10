const byId = (id) => document.getElementById(id);
const solutionInput = byId('solution-file');
const studentInput = byId('student-file');
let toastTimer;

function showToast(message, isError = false) {
  const toast = byId('toast');
  toast.textContent = message;
  toast.style.background = isError ? '#8f3039' : '#25273b';
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3000);
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Something went wrong.');
  return data;
}

function addTextFileList(listElement, files, emptyMessage) {
  listElement.replaceChildren();
  if (!files.length) {
    const item = document.createElement('li');
    item.className = 'empty-list';
    item.textContent = emptyMessage;
    listElement.append(item);
    return;
  }
  files.forEach((file) => {
    const item = document.createElement('li');
    item.textContent = file;
    listElement.append(item);
  });
}

function fileOptions(files, selected, placeholder) {
  const select = document.createElement('select');
  const empty = document.createElement('option');
  empty.value = '';
  empty.textContent = placeholder;
  select.append(empty);
  files.filter((file) => file.toLowerCase().endsWith('.py')).forEach((file) => {
    const option = document.createElement('option');
    option.value = file;
    option.textContent = file;
    select.append(option);
  });
  if (selected && [...select.options].some((option) => option.value === selected)) {
    select.value = selected;
  }
  return select;
}

function appendMappingRow(solutionFiles, studentFiles, mapping = {}) {
  const container = byId('mapping-rows');
  const row = document.createElement('div');
  row.className = 'mapping-row';

  const top = document.createElement('div');
  top.className = 'mapping-row-top';
  const label = document.createElement('span');
  label.textContent = `PAIR ${container.children.length + 1}`;
  const remove = document.createElement('button');
  remove.type = 'button';
  remove.className = 'remove-row';
  remove.setAttribute('aria-label', 'Remove comparison');
  remove.textContent = '×';
  remove.addEventListener('click', () => {
    row.remove();
    renumberRows();
  });
  top.append(label, remove);

  const solutionLabel = document.createElement('label');
  solutionLabel.textContent = 'Solution file';
  const solutionSelect = fileOptions(solutionFiles, mapping.solution_file, 'Choose solution .py');
  solutionSelect.className = 'solution-select';
  solutionLabel.append(solutionSelect);

  const studentLabel = document.createElement('label');
  studentLabel.textContent = 'Student file';
  const studentSelect = fileOptions(studentFiles, mapping.student_file, 'Choose student .py');
  studentSelect.className = 'student-select';
  studentLabel.append(studentSelect);

  row.append(top, solutionLabel, studentLabel);
  container.append(row);
}

function renumberRows() {
  [...byId('mapping-rows').children].forEach((row, index) => {
    row.querySelector('.mapping-row-top span').textContent = `PAIR ${index + 1}`;
  });
}

function renderMappings(state) {
  const container = byId('mapping-rows');
  container.replaceChildren();
  const solutionPython = state.solution_files.filter((file) => file.toLowerCase().endsWith('.py'));
  const studentPython = state.student_files.filter((file) => file.toLowerCase().endsWith('.py'));
  byId('add-comparison').disabled = !solutionPython.length || !studentPython.length;
  byId('save-comparisons').disabled = !state.solution;
  (state.comparisons || []).forEach((mapping) => appendMappingRow(solutionPython, studentPython, mapping));
}

function renderState(state) {
  byId('solution-summary').textContent = state.solution
    ? `Loaded: ${state.solution.archive_name}`
    : 'No solution loaded';
  byId('solution-count').textContent = state.solution_files.length;
  byId('student-count').textContent = `${state.student_files.length} file${state.student_files.length === 1 ? '' : 's'}`;
  byId('student-name').value = state.student?.name || '';
  byId('student-id').value = state.student?.student_id || '';
  addTextFileList(byId('solution-files'), state.solution_files, 'No files yet');
  addTextFileList(byId('student-files'), state.student_files, 'Upload a student ZIP to see files here');
  renderMappings(state);
}

async function refreshState() {
  renderState(await requestJson('/api/state'));
}

function setBusy(button, busy, text) {
  button.disabled = busy;
  if (busy) {
    button.dataset.originalText = button.textContent;
    button.textContent = text;
  } else if (button.dataset.originalText) {
    button.textContent = button.dataset.originalText;
    delete button.dataset.originalText;
  }
}

function wireDropzone(input, zone, filenameLabel) {
  input.addEventListener('change', () => {
    filenameLabel.textContent = input.files[0]?.name || 'No ZIP selected';
  });
  ['dragenter', 'dragover'].forEach((eventName) => zone.addEventListener(eventName, (event) => {
    event.preventDefault();
    zone.classList.add('drag-over');
  }));
  ['dragleave', 'drop'].forEach((eventName) => zone.addEventListener(eventName, (event) => {
    event.preventDefault();
    zone.classList.remove('drag-over');
  }));
  zone.addEventListener('drop', (event) => {
    const file = event.dataTransfer.files[0];
    if (!file) return;
    const transfer = new DataTransfer();
    transfer.items.add(file);
    input.files = transfer.files;
    filenameLabel.textContent = file.name;
  });
}

wireDropzone(solutionInput, byId('solution-drop'), byId('solution-filename'));
wireDropzone(studentInput, byId('student-drop'), byId('student-filename'));

byId('extract-solution').addEventListener('click', async (event) => {
  const button = event.currentTarget;
  if (!solutionInput.files[0]) return showToast('Choose a solution ZIP first.', true);
  const form = new FormData();
  form.append('archive', solutionInput.files[0]);
  setBusy(button, true, 'Extracting…');
  try {
    renderState(await requestJson('/api/solutions/extract', { method: 'POST', body: form }));
    byId('results').replaceChildren();
    byId('results-summary').textContent = 'Solution extracted. Upload a student ZIP and set file pairings.';
    showToast('Solution ZIP extracted.');
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(button, false);
  }
});

byId('extract-student').addEventListener('click', async (event) => {
  const button = event.currentTarget;
  if (!studentInput.files[0]) return showToast('Choose a student ZIP first.', true);
  const form = new FormData();
  form.append('archive', studentInput.files[0]);
  form.append('name', byId('student-name').value);
  form.append('student_id', byId('student-id').value);
  setBusy(button, true, 'Extracting…');
  try {
    renderState(await requestJson('/api/student/extract', { method: 'POST', body: form }));
    byId('results').replaceChildren();
    byId('results-summary').textContent = 'Student ZIP extracted. Review or add file pairings, then run the comparisons.';
    showToast('Student ZIP extracted into the workspace.');
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(button, false);
  }
});

byId('add-comparison').addEventListener('click', async () => {
  const state = await requestJson('/api/state');
  appendMappingRow(
    state.solution_files.filter((file) => file.toLowerCase().endsWith('.py')),
    state.student_files.filter((file) => file.toLowerCase().endsWith('.py')),
  );
});

byId('save-comparisons').addEventListener('click', async (event) => {
  const button = event.currentTarget;
  const comparisons = [...byId('mapping-rows').children].map((row) => ({
    solution_file: row.querySelector('.solution-select').value,
    student_file: row.querySelector('.student-select').value,
  }));
  if (!comparisons.length) return showToast('Add at least one comparison first.', true);
  if (comparisons.some((row) => !row.solution_file || !row.student_file)) {
    return showToast('Choose both files for every comparison.', true);
  }
  setBusy(button, true, 'Saving…');
  try {
    await requestJson('/api/comparisons', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ comparisons }),
    });
    showToast('Comparison settings saved.');
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(button, false);
  }
});

function outputColumn(title, text) {
  const column = document.createElement('div');
  column.className = 'output-column';
  const label = document.createElement('div');
  label.className = 'output-label';
  const heading = document.createElement('span');
  heading.textContent = title;
  const raw = document.createElement('em');
  raw.textContent = 'raw stdout';
  label.append(heading, raw);
  const output = document.createElement('pre');
  output.className = 'output-text';
  output.textContent = text;
  column.append(label, output);
  return column;
}

function renderResults(data) {
  const container = byId('results');
  container.replaceChildren();
  data.results.forEach((result) => {
    const card = document.createElement('article');
    card.className = 'result-card';
    const top = document.createElement('div');
    top.className = 'result-top';
    const pair = document.createElement('div');
    pair.className = 'result-pair';
    const strong = document.createElement('strong');
    strong.textContent = result.solution_file;
    const arrow = document.createTextNode(`  →  ${result.student_file}`);
    pair.append(strong, arrow);
    const status = document.createElement('span');
    status.className = `status ${result.status === 'MATCH' ? 'status-match' : result.status === 'MISMATCH' ? 'status-mismatch' : 'status-error'}`;
    status.textContent = result.status;
    top.append(pair, status);
    const columns = document.createElement('div');
    columns.className = 'output-columns';
    columns.append(outputColumn('Expected', result.expected), outputColumn('Actual', result.actual));
    card.append(top, columns);
    const errors = [
      result.expected_error && `Expected run: ${result.expected_error}`,
      result.expected_stderr && `Expected stderr:\n${result.expected_stderr}`,
      result.actual_error && `Student run: ${result.actual_error}`,
      result.actual_stderr && `Student stderr:\n${result.actual_stderr}`,
    ].filter(Boolean);
    if (errors.length) {
      const errorPanel = document.createElement('div');
      errorPanel.className = 'run-error';
      errorPanel.textContent = errors.join('\n\n');
      card.append(errorPanel);
    }
    container.append(card);
  });
  const name = data.student?.name || 'Student';
  const id = data.student?.student_id ? ` · ${data.student.student_id}` : '';
  const matches = data.results.filter((result) => result.status === 'MATCH').length;
  byId('results-summary').textContent = `${name}${id} · ${matches} of ${data.results.length} comparisons match exactly.`;
}

byId('run-comparisons').addEventListener('click', async (event) => {
  const button = event.currentTarget;
  setBusy(button, true, 'Running…');
  try {
    renderResults(await requestJson('/api/run', { method: 'POST' }));
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(button, false);
  }
});

refreshState().catch((error) => showToast(error.message, true));
