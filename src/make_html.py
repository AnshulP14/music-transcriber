"""Interactive score page (OSMD render, playback cursor, metronome, note table) -> out/score.html."""
import csv, json
from collections import Counter
from common import OUT, SOURCE, SONG, KEY, SHARP, Grid, load, pc_of

grid = Grid(); M = load('melody.json'); ch = load('accomp.json')['chords']; bpm = grid.bpm
xml = (OUT / 'score.musicxml').read_text(encoding='utf-8').replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')
BT = [round(x, 3) for x in grid.beats[grid.B0:].tolist()]
nice = lambda c: c.replace('-', '♭')
audio = '../source/' + next(SOURCE.glob('song.*')).name
key_label = f"{nice(KEY.tonic.name)} {KEY.mode}"
accs = [p.name for p in KEY.alteredPitches]  # e.g. B- E- A- D-
acc_label = f"{len(accs)} {'flats' if KEY.sharps < 0 else 'sharps'}" if accs else 'no sharps or flats'
used = sorted(set(ch), key=ch.index); top = sorted([c for c, _ in Counter(ch).most_common(4)], key=ch.index)
as_sharp = lambda c: SHARP[pc_of(c.rstrip('m'))] + ('m' if c.endswith('m') else '')
flat_chords = ', '.join(f'{nice(c)} = {as_sharp(c)}' for c in used if '-' in c)
guide = [f"<b>Most used chords:</b> <b>{', '.join(map(nice, top))}</b>."]
guide.append('<b>Chord names</b> above the top staff appear when the chord changes' + (f' ({flat_chords}).' if flat_chords else '.'))
if accs: guide.append(f"<b>{acc_label} at the start</b> ({', '.join(a[0] for a in accs)}) = always play those on their black keys."
                      + (f" The staff spells them as flats; the letters use sharps ({', '.join(f'{nice(a)} = {SHARP[pc_of(a)]}' for a in accs)})." if KEY.sharps < 0 else ''))
bars = {}
for r in csv.DictReader(open(OUT / 'lyrics_alignment.csv')): bars.setdefault(int(r['bar']), []).append(r)
tbl=''
for b in range(1,grid.nbars+1):
    c1,c2=ch[2*(b-1)],ch[2*(b-1)+1]; cs=nice(c1) if c1==c2 else nice(c1)+' | '+nice(c2)
    cells=''.join(f"<td data-t=\"{r['time_s']}\"><b>{r['key']}</b><i>{r['count']}</i><em>{float(r['length_beats']):g}</em></td>" for r in bars.get(b,[])) or '<td class="r">rest</td>'
    tbl+=f"<tr><th>Bar {b}<br><small>{cs}</small></th>{cells}</tr>"
html='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>'''+SONG['title']+''' - score</title>
<style>:root{--bg:#fafafa;--fg:#222;--card:#fff;--mut:#555;--line:#ddd}@media(prefers-color-scheme:dark){:root{--bg:#1b1b1b;--fg:#eee;--card:#262626;--mut:#aaa;--line:#444}}
body{font-family:system-ui,sans-serif;margin:0;background:var(--bg);color:var(--fg)}header{padding:12px 24px;background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:2}
h1{font-size:18px;margin:0 0 4px}h2{font-size:16px;margin:0 0 8px}p,li{font-size:14px;color:var(--mut);line-height:1.5}button{font-size:15px;padding:6px 14px;margin:6px 8px 0 0;border:1px solid #888;border-radius:6px;background:var(--card);color:var(--fg);cursor:pointer}
button.on{background:#222;color:#fff}input{vertical-align:middle}audio{vertical-align:middle;height:32px;margin-top:6px;max-width:100%}.card{padding:16px 24px;background:#fff;margin:16px auto;max-width:1100px;border:1px solid var(--line);border-radius:8px;overflow-x:auto}.card.t{background:var(--card)}#b{display:inline-block;width:18px;height:18px;border-radius:50%;background:#ccc;vertical-align:middle;margin-left:6px}
table{border-collapse:collapse;font-size:13px}td,th{border:1px solid var(--line);padding:4px 7px;text-align:center;white-space:nowrap}th{text-align:left;background:var(--bg);position:sticky;left:0}td b{display:block;font-size:16px;color:var(--fg)}td i{display:block;color:#36c;font-style:normal}td em{display:block;color:var(--mut);font-style:normal;font-size:11px}td.r{color:var(--mut)}td.cur{background:#ffe08a;outline:2px solid #e3a800}td.cur b{color:#000}select{font-size:14px;padding:4px;margin:6px 6px 0 0}</style></head><body>
<header><h1>'''+SONG['title']+''' — piano score (auto-transcribed)</h1>
<p>'''+key_label+' ('+acc_label+''') · 4/4 · '''+str(bpm)+''' BPM · '''+SONG.get('artist','').replace('&','&amp;')+''' · lyrics not included</p>
<button id="m">Start metronome</button> BPM <input id="bpm" type="number" value="'''+str(bpm)+'''" min="40" max="200" style="width:60px"> <span id="b"></span>
<br><select id="src"><option value="'''+audio+'''">Song</option><option value="check_mix.mp3">Song + melody beeps</option><option value="check_accompaniment.mp3">Song + piano part beeps</option></select>
<select id="rate"><option value="1">1× speed</option><option value="0.75">0.75×</option><option value="0.5">0.5×</option></select>
<audio id="au" controls src="'''+audio+'''"></audio> <label><input type="checkbox" id="follow" checked> follow</label></header>
<div class="card t"><h2>How to read this</h2><ul>
<li><b>Letters under the notes</b> = piano key to press. <b>#</b> = the black key just above that white key (A# is the black key right above A).</li>
<li><b>Staves.</b> <b>Top</b> = the sung melody (written an octave above sung pitch), for reference — sing it. <b>Middle + bottom (joined by a brace)</b> = the piano part to play while you sing.</li>'''+(f"<li><b>2nd voice</b> (staff under the melody, only in bars {', '.join(map(str, M['duet']))}) = a second singer singing a different line at the same time. The top staff stays on one singer; play or sing whichever you like.</li>" if M['duet'] else '')+'''<li><b>Piano left hand</b> = the song's real bass line, taken from the bass guitar. It mostly repeats the chord's root with a push on <b>2-a</b> and a short run into the next chord.</li><li><b>Piano right hand</b> = 3-note chord, hit on <b>1</b>, <b>2-a</b> and <b>4</b> (the off-beat 2-a hit already plays the chord that starts on beat 3 — the song's 'push'). Quiet bars just hold one chord per half bar.</li>
'''+''.join(f'<li>{g}</li>' for g in guide)+'''
<li><b>Timing:</b> 4 beats per bar = 4 metronome clicks. Beamed short notes are 16ths (4 per beat), counted <b>1 e &amp; a 2 e &amp; a</b>… The table below shows each note's count.</li>
'''+''.join(f'<li>{n}</li>' for n in SONG.get('notes', []))+'''
<li><b>Playback:</b> press play — a cursor follows the music, the notes at that moment turn <span style=\"color:#e33\">red</span>, and the table cell lights up. Pick <i>Song + melody beeps</i> or <i>Song + piano part beeps</i> to hear my transcription over the record (a clash = wrong note), and 0.75×/0.5× to slow down.</li></ul></div>
<div class="card"><p id="ld">Loading score…</p><div id="o"></div></div>
<div class="card t"><h2>Note by note</h2><p>Each cell: <b>key</b>, <span style="color:#36c">count</span> where it starts, length in beats. Row header = bar and chord(s). The cells are the melody only.</p><table>'''+tbl+'''</table></div>
<script src="https://cdn.jsdelivr.net/npm/opensheetmusicdisplay@1.8.9/build/opensheetmusicdisplay.min.js"></script>
<script>
const XML=`'''+xml+'''`;
const o=new opensheetmusicdisplay.OpenSheetMusicDisplay("o",{autoResize:true,drawPartNames:false,drawTitle:false,drawSubtitle:false,drawComposer:false,drawMeasureNumbers:true});
const BT='''+json.dumps(BT)+''';
const au=document.getElementById("au");let steps=[],cur=-1,colored=[];
function beatAt(t){if(t<BT[0])return -1;let lo=0,hi=BT.length-1;if(t>=BT[hi])return hi;while(hi-lo>1){const m=(lo+hi)>>1;if(BT[m]<=t)lo=m;else hi=m}return lo+(t-BT[lo])/(BT[lo+1]-BT[lo])}
o.load(XML).then(()=>{o.render();document.getElementById("ld").remove();const c=o.cursor;c.show();c.reset();
 while(!c.Iterator.EndReached){steps.push(c.Iterator.currentTimeStamp.RealValue*4);c.next()}
 c.reset();c.hide();sync()}).catch(e=>{document.getElementById("o").textContent="Render error: "+e});
function paint(){colored.forEach(([p,f])=>f===null?p.removeAttribute("fill"):p.setAttribute("fill",f));colored=[];
 try{o.cursor.GNotesUnderCursor().forEach(g=>{const el=g.getSVGGElement&&g.getSVGGElement();if(!el)return;
  el.querySelectorAll("path").forEach(p=>{colored.push([p,p.getAttribute("fill")]);p.setAttribute("fill","#e33")})})}catch(e){}}
function moveTo(idx){const c=o.cursor;if(idx<0){if(cur>=0){c.hide();colored.forEach(([p,f])=>f===null?p.removeAttribute("fill"):p.setAttribute("fill",f));colored=[]}cur=-1;return}
 if(cur<0||idx<cur){c.show();c.reset();cur=0}while(cur<idx){c.next();cur++}paint();
 if(document.getElementById("follow").checked&&c.cursorElement){const r=c.cursorElement.getBoundingClientRect();if(r.top<120||r.bottom>innerHeight-20)c.cursorElement.scrollIntoView({block:"center",behavior:"smooth"})}}
const tds=[...document.querySelectorAll("td[data-t]")];let curTd=null;
function sync(){if(!steps.length)return;const b=beatAt(au.currentTime);let idx=-1;
 if(b>=0){let lo=0,hi=steps.length-1;if(steps[0]>b+0.02)idx=-1;else{while(lo<hi){const m=(lo+hi+1)>>1;if(steps[m]<=b+0.02)lo=m;else hi=m-1}idx=lo}}
 if(idx!==cur)moveTo(idx);
 let td=null;for(const x of tds){if(+x.dataset.t<=au.currentTime+0.02)td=x;else break}
 if(td!==curTd){curTd&&curTd.classList.remove("cur");td&&td.classList.add("cur");curTd=td}}
(function loop(){if(!au.paused)sync();requestAnimationFrame(loop)})();
au.addEventListener("seeked",sync);au.addEventListener("timeupdate",sync);
document.getElementById("src").onchange=e=>{const t=au.currentTime,p=!au.paused;au.src=e.target.value;au.addEventListener("loadedmetadata",()=>{au.currentTime=t;au.playbackRate=+document.getElementById("rate").value;if(p)au.play()},{once:true})};
document.getElementById("rate").onchange=e=>{au.playbackRate=+e.target.value;au.preservesPitch=true};
let ctx,timer,n=0;const btn=document.getElementById("m"),dot=document.getElementById("b");
function click(acc){const t=ctx.currentTime,os=ctx.createOscillator(),g=ctx.createGain();os.frequency.value=acc?1500:1000;g.gain.setValueAtTime(.4,t);g.gain.exponentialRampToValueAtTime(.001,t+.06);os.connect(g).connect(ctx.destination);os.start(t);os.stop(t+.07);dot.style.background=acc?"#d33":"#39c";setTimeout(()=>dot.style.background="#ccc",80)}
btn.onclick=()=>{if(timer){clearInterval(timer);timer=null;btn.textContent="Start metronome";btn.classList.remove("on");return}
ctx=ctx||new AudioContext();const ms=60000/Math.max(40,Math.min(200,+document.getElementById("bpm").value||74));
click(true);n=1;timer=setInterval(()=>{click(n%4===0);n++},ms);btn.textContent="Stop metronome";btn.classList.add("on")};
</script></body></html>'''
(OUT / 'score.html').write_text(html, encoding='utf-8')
print(OUT / 'score.html')
