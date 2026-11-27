// Голосование клиента (стеллаж, шторы, обои). Ответы пишутся в эту таблицу.
// Пароль сводки хранится в свойствах скрипта (Project Settings → Script Properties → PASSWORD),
// чтобы его не было в репозитории.
var PASSWORD = PropertiesService.getScriptProperties().getProperty('PASSWORD') || '';
var SHEET = 'Ответы';
var LABEL = {y:'Нравится', m:'Возможно', n:'Не подходит'};
var COLS = 7; // Время | Голосующий | Ключ | ID | Вариант | Ответ | Категория
// Категория по префиксу id: без префикса — стеллаж (старые id не менялись).
var CATS = {curtain: 'Шторы', wallpaper: 'Обои', combo: 'Гостиная: сочетания'};
function category_(id) {
  var m = String(id).match(/^([a-z]+):/);
  return m && CATS[m[1]] ? CATS[m[1]] : 'Стеллаж';
}

function doGet(e) {
  var url = 'https://bogdankewich.github.io/stellazh/' + (e && e.parameter && 'admin' in e.parameter ? '?admin' : '');
  return HtmlService.createHtmlOutput('<p>Страница переехала: <a href="' + url + '" target="_top">' + url + '</a></p>').setTitle('Выбор вариантов');
}

function sheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(SHEET) || ss.getSheets()[0];
  if (sh.getName() !== SHEET) sh.setName(SHEET);
  if (sh.getLastRow() === 0) sh.appendRow(['Время', 'Голосующий', 'Ключ', 'ID', 'Вариант', 'Ответ', 'Категория']);
  else if (!sh.getRange(1, 7).getValue()) sh.getRange(1, 7).setValue('Категория');
  return sh;
}

// voters: {key:{name, v:{id:'y'|'m'|'n'}}}; names: {id: 'Производитель Модель'}
function saveVotes(voters, names) {
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var sh = sheet_();
    var keys = Object.keys(voters || {}).map(function (k) { return String(k).slice(0, 40); });
    if (!keys.length) return 'ok';
    var last = sh.getLastRow();
    var rows = last > 1 ? sh.getRange(2, 1, last - 1, COLS).getValues() : [];
    var keep = rows.filter(function (r) { return keys.indexOf(String(r[2])) < 0; });
    keep.forEach(function (r) { if (!r[6] && r[3] !== '') r[6] = category_(r[3]); });
    var now = Utilities.formatDate(new Date(), 'Europe/Andorra', 'yyyy-MM-dd HH:mm');
    Object.keys(voters).forEach(function (k) {
      var o = voters[k] || {}, v = o.v || {};
      var name = String(o.name || k).slice(0, 40);
      Object.keys(v).forEach(function (id) {
        if (!LABEL[v[id]]) return;
        keep.push([now, name, String(k).slice(0, 40), String(id).slice(0, 40), String((names || {})[id] || id).slice(0, 120), LABEL[v[id]], category_(id)]);
      });
    });
    if (last > 1) sh.getRange(2, 1, last - 1, COLS).clearContent();
    if (keep.length) sh.getRange(2, 1, keep.length, COLS).setValues(keep);
    return 'ok';
  } finally {
    lock.releaseLock();
  }
}

function checkPassword(pw) { return !!PASSWORD && pw === PASSWORD; }

function getAll(pw) {
  if (!PASSWORD || pw !== PASSWORD) throw new Error('bad password');
  var sh = sheet_(), last = sh.getLastRow();
  var rows = last > 1 ? sh.getRange(2, 1, last - 1, 6).getValues() : [];
  var code = {'Нравится': 'y', 'Возможно': 'm', 'Не подходит': 'n'};
  var voters = {};
  rows.forEach(function (r) {
    var k = String(r[2]); if (!k) return;
    var o = voters[k] || (voters[k] = {name: String(r[1]), v: {}, t: 0});
    if (code[r[5]]) o.v[String(r[3])] = code[r[5]];
  });
  return voters;
}

// Для страницы на GitHub Pages: запросы приходят через POST.
function doPost(e) {
  var out;
  try {
    var req = JSON.parse(e.postData.contents || '{}'), d = req.data || {};
    var result;
    if (req.action === 'save') result = saveVotes(d.voters, d.names);
    else if (req.action === 'check') result = checkPassword(d.pw);
    else if (req.action === 'all') result = getAll(d.pw);
    else throw new Error('unknown action');
    out = {result: result};
  } catch (err) {
    out = {error: String(err && err.message || err)};
  }
  return ContentService.createTextOutput(JSON.stringify(out)).setMimeType(ContentService.MimeType.JSON);
}

// Один раз вручную (Run → fillCategories): проставить «Категория» у уже записанных строк.
function fillCategories() {
  var sh = sheet_(), last = sh.getLastRow();
  if (last < 2) return;
  var r = sh.getRange(2, 1, last - 1, COLS), v = r.getValues();
  v.forEach(function (x) { if (!x[6] && x[3] !== '') x[6] = category_(x[3]); });
  r.setValues(v);
}
