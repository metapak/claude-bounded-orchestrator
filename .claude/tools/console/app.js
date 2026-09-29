'use strict';
const $ = id => document.getElementById(id);
const token = new URLSearchParams(location.hash.slice(1)).get('token') || '';
history.replaceState(null, '', '/');
let config, revision;
async function api(path, data) {
  const headers = {'X-Console-Token': token};
  if (data !== undefined) headers['Content-Type'] = 'application/json';
  const response = await fetch('/api/' + path, {method: data === undefined ? 'GET' : 'POST', headers, body: data === undefined ? undefined : JSON.stringify(data)});
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'İşlem başarısız');
  return value;
}
function status(message) { $('status').textContent = message; }
function node(tag, text, className) { const el = document.createElement(tag); if(text !== undefined) el.textContent = text; if(className) el.className = className; return el; }
async function action(fn) { try { await fn(); } catch (error) { status(error.message); } }
function invalidate() { revision = undefined; $('preview-panel').hidden = true; }
function roles(routing) {
  $('roles').replaceChildren();
  for (const [role, values] of Object.entries(routing)) {
    const row = node('tr'); row.dataset.role = role;
    row.append(node('td', role));
    const model = node('input'); model.value = values.model; model.setAttribute('aria-label', role + ' modeli'); model.maxLength = 128;
    const effort = node('select'); effort.setAttribute('aria-label', role + ' effort');
    for (const value of ['low','medium','high','xhigh',...(role === 'owner' ? [] : ['max'])]) { const option=node('option',value); option.value=value; effort.append(option); }
    effort.value=values.effort;
    for(const element of [model,effort]) { const cell=node('td'); cell.append(element);row.append(cell); element.addEventListener('input',()=>{invalidate();$('preset').value='custom';}); }
    $('roles').append(row);
  }
}
function payload() { const routing={}; for(const row of $('roles').children) routing[row.dataset.role]={model:row.querySelector('input').value,effort:row.querySelector('select').value}; return {preset:$('preset').value,routing,max_parallelism:Number($('parallel').value),...(revision ? {revision}: {})}; }
async function refresh() { config=await api('settings'); $('target').textContent='Proje: '+config.target; $('preset').value=config.preset; $('parallel').value=config.max_parallelism || 1; $('settings-limits').textContent=config.limitations; $('restore').disabled=!config.restore_available; roles(config.routing);invalidate(); }
for (const button of document.querySelectorAll('[data-tab]')) button.addEventListener('click',()=>action(async()=>{for(const item of document.querySelectorAll('[data-tab]')) {item.classList.toggle('active',item===button);if(item===button)item.setAttribute('aria-current','page');else item.removeAttribute('aria-current');} for(const id of ['settings','usage','tasks'])$(id).hidden=id!==button.dataset.tab;if(button.dataset.tab==='tasks')await tasks();}));
$('preset').addEventListener('change',()=>{invalidate();if(config.presets[$('preset').value])roles(config.presets[$('preset').value]);});
$('parallel').addEventListener('input',invalidate);
$('preview').addEventListener('click',()=>action(async()=>{const value=await api('preview',payload());revision=value.revision;$('preview-text').textContent=JSON.stringify(value,null,2);$('preview-panel').hidden=false;status('Önizleme hazır. Henüz dosya yazılmadı.');}));
$('save').addEventListener('click',()=>action(async()=>{await api('save',payload());await refresh();status('Seçilen proje kaydedildi. Claude Code’u yeniden başlatın.');}));
$('restore').addEventListener('click',()=>action(async()=>{await api('restore',{});await refresh();status('Önceki konsol güncellemesi geri yüklendi.');}));
$('load-usage').addEventListener('click',()=>action(async()=>{
  const data=await api('usage',{path:$('source').value,start:$('start').value,end:$('end').value});
  const box=$('usage-result');box.replaceChildren(node('p',data.status==='available'?'Ölçümler mevcut · Kaynak: açıkça seçilen OTLP':'Veri bulunamadı','note'));
  if(data.message)box.append(node('p',data.message,'empty'));
  const cards=node('div',undefined,'cards');for(const [kind,value] of Object.entries(data.totals)){const card=node('div',kind,'card');card.append(node('strong',value.toLocaleString('tr-TR')));cards.append(card);}box.append(cards);
  box.append(node('p','Maliyet: '+(Object.keys(data.cost_totals).length ? 'OTLP tarafından bildirilen ölçümler; tahmin değil. '+JSON.stringify(data.cost_totals) : 'Mevcut değil.')));
  const dimensions=node('p',Object.entries(data.dimensions).map(([k,v])=>k+': '+(v?'mevcut':'mevcut değil')).join(' · '),'note');box.append(dimensions);
  const table=node('table');const header=node('tr');for(const label of ['Model','Tür','Birim','Değer'])header.append(node('th',label));const head=node('thead');head.append(header);table.append(head);const body=node('tbody');for(const group of data.groups){const row=node('tr');for(const key of ['model','type','unit','value'])row.append(node('td',String(group[key])));body.append(row);}table.append(body);box.append(table);
  const details=node('details');details.append(node('summary','Tarih / oturum / ajan ölçümleri'));const pre=node('pre',JSON.stringify(data.events,null,2));details.append(pre);box.append(details);
  box.append(node('p',data.limitations,'note'));status('Kullanım raporu güncellendi.');
}));
async function tasks(){const data=await api('tasks');const box=$('task-result');box.replaceChildren(node('p',data.message,'note'));if(!data.tasks.length)box.append(node('p','Bu proje için kayıtlı görev yok.','empty'));for(const task of data.tasks){const el=node('article',undefined,'task');el.append(node('h3',task.id+' · '+task.status));el.append(node('p',task.summary));el.append(node('pre',JSON.stringify(task,null,2)));box.append(el);}}
action(refresh);
