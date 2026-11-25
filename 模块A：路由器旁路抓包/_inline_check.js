
const D = window.DEMO_DATA;
const STEPS = [
  {n:"01",ic:"📡",t:"旁路抓包",d:"br-lan 镜像 + BPF 严格过滤",
   body:"<b>做了什么</b>：在路由器 <span class='label'>br-lan</span> 上用 libpcap 抓 TCP 8195 端口、且只针对游戏 PC 的 IP。<br><b>为什么</b>：被动只读，不发包、不注入、不改内存；BPF 在内核层过滤，既合规又省 MIPS 算力。"},
  {n:"02",ic:"🧩",t:"TCP 重组",d:"按 flow 拼段，gap_timeout 兜底",
   body:"<b>做了什么</b>：按 flow_id 把 TCP 段重组成完整游戏帧；丢段超过阈值触发 resync。<br><b>为什么</b>：背包帧（4934/PetBox）体积大、跨几十个 TCP 段，任一段丢失整帧就废。这是真实链路里最容易被忽略的坑。"},
  {n:"03",ic:"🔐",t:"会话解密",d:"0x1002 密钥 + AES-128 CBC",
   body:"<b>做了什么</b>：会话密钥 0x1002 只在 TCP 建连瞬间下发，用它解密后续帧。<br><b>为什么</b>：所以抓包必须先启动、再让游戏断网 3 秒重连；否则密钥库为空，解出来全是 <span class='warn'>decrypt_fail</span>。"},
  {n:"04",ic:"🔎",t:"opcode 门控",d:"258 / 4934 / 6273… 分类处理",
   body:"<b>做了什么</b>：258 解 profile 拿 game_id，4934 解 PetData，6273/6275/6277/6289 解 PetBox，其余直接跳过。<br><b>为什么</b>：880MHz MIPS 上全帧扫描会拖垮抓包；门控让背包解析不影响战斗实时链路。"},
  {n:"05",ic:"🧬",t:"字段白名单",d:"只取数值与固定 kind",
   body:"<b>做了什么</b>：protobuf 还原时只保留数值字段和约定字段，名字只在本地用 catalog 还原。<br><b>为什么</b>：契约层不夹带玩家名、账号名、IP、端口——隐私最小化是设计约束，不是事后补丁。"},
  {n:"06",ic:"📦",t:"结构化快照",d:"26 盒 / 593 只 / 可同步",
   body:"<b>做了什么</b>：按 uid 攒会话，静默 8 秒落盘为 boxes JSON，用户在面板点「同步」才上传。<br><b>为什么</b>：同一 IP 可能双开多个账号，归属靠 game_id 而非 IP；默认不同步把数据所有权还给用户。"},
];

const pipe = document.getElementById("pipe");
const detail = document.getElementById("detail");
const consoleEl = document.getElementById("console");
STEPS.forEach((s,i)=>{
  const el = document.createElement("div");
  el.className = "step"; el.dataset.i = i;
  el.innerHTML = `<div class="n">STEP ${s.n}</div><div class="ic">${s.ic}</div><div class="t">${s.t}</div><div class="d">${s.d}</div>`;
  el.onclick = ()=>showStep(i);
  pipe.appendChild(el);
});
function showStep(i){
  [...pipe.children].forEach((c,j)=>c.classList.toggle("on",j===i));
  detail.innerHTML = `<span style="color:var(--dim)">STEP ${STEPS[i].n}</span> · ${STEPS[i].body}`;
}

// stats
const st = D.stats;
document.getElementById("stats").innerHTML = [
  [st.boxCount,"盒子"],[st.petCount,"精灵"],[st.shinyCount,"异色"],[st.colorfulCount,"炫彩"]
].map(([v,l])=>`<div class="stat"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");

// boxes
const boxEl = document.getElementById("boxes");
const petEl = document.getElementById("pets");
D.boxes.forEach((b,i)=>{
  const sh = b.pets.filter(p=>p.isShiny).length;
  const co = b.pets.filter(p=>p.isColorful).length;
  const el = document.createElement("div");
  el.className = "box";
  el.innerHTML = `<div class="top"><span>#${b.boxNumber} ${b.boxName||""}</span><span class="cnt">${b.count}/30</span></div>
    <div class="bar-mini"><i style="width:${Math.min(100,b.count/30*100)}%"></i></div>
    <div><span class="pill sh">✦ ${sh}</span> <span class="pill co">❖ ${co}</span></div>`;
  el.onclick = ()=>{
    [...boxEl.children].forEach(c=>c.classList.remove("on"));
    el.classList.add("on");
    renderPets(b);
  };
  boxEl.appendChild(el);
});
function renderPets(box){
  const pets = box.pets.filter(p=>p.name && p.name.trim());
  petEl.innerHTML = `<div style="grid-column:1/-1;color:var(--sub);font-size:13px;margin-top:8px">
    <b style="color:var(--ink)">盒子 #${box.boxNumber}</b> · 展示 ${pets.length} 只（已脱敏：无捕获时间/来源坐标）</div>` +
    pets.slice(0,24).map(p=>{
      const cls = p.isShiny?"sh":p.isColorful?"co":"";
      const dot = p.isShiny?'<span class="dot sh" title="异色"></span>':p.isColorful?'<span class="dot co" title="炫彩"></span>':'';
      return `<div class="pet ${cls}"><div class="nm">${dot}${p.name} <span style="color:var(--dim)">${p.gender||""}</span></div>
        <div class="meta">${p.nature||"—"} · Lv.${p.level||"—"} · ${p.weightKg!=null?p.weightKg+"kg":""}</div>
        <div class="meta">${p.bloodline||"—"}</div></div>`;
    }).join("") + (pets.length>24?`<div style="color:var(--dim);font-size:12px;padding:10px">…还有 ${pets.length-24} 只</div>`:"");
}

// playback
const logs = [
  ["$ capture start --iface br-lan --bpf 'tcp port 8195 and host <game-pc>'","hi"],
  ["  [01] BPF filter installed · passive read-only","ok"],
  ["  [02] flow created · waiting for 0x1002 ...",""],
  ["$ 游戏断网 3 秒重连 → 新密钥下发","warn"],
  ["  [03] key_captured · AES-128 CBC ready","ok"],
  ["  [04] opcode 258  → profile.f1 = game_id (Miffy)",""],
  ["  [04] opcode 4934 → PetData page 1/... ",""],
  ["  [04] opcode 6273 → PetBox page 1/... ",""],
  ["  ... 翻盒到底，静默 8 秒无新帧 → 会话结算",""],
  [`  [05] whitelist fields only · no UID / no player name / no key`,"ok"],
  [`  [06] snapshot ready · ${st.boxCount} boxes / ${st.petCount} pets / ${st.shinyCount} shiny`,"ok"],
  ["$ done · 默认不上传，等待用户显式同步","hi"],
];
let timer = null;
document.getElementById("run").onclick = ()=>{
  if(timer) return;
  const btn = document.getElementById("run"); btn.disabled = true;
  consoleEl.textContent = "";
  logs.forEach((line,i)=>{
    setTimeout(()=>{
      const div = document.createElement("div");
      if(line[1]) div.className = line[1];
      div.textContent = line[0];
      consoleEl.appendChild(div);
      consoleEl.scrollTop = consoleEl.scrollHeight;
      if(i%2===0) showStep(Math.min(Math.floor(i/2),5));
    },i*320);
  });
  setTimeout(()=>{btn.disabled=false;},logs.length*320+200);
};
document.getElementById("reset").onclick = ()=>{
  if(timer) return;
  consoleEl.textContent = "$ waiting for capture...";
  [...pipe.children].forEach(c=>c.classList.remove("on"));
  detail.innerHTML = "点击上方任一节点，查看该环节做了什么、以及为什么这么设计。";
  boxEl.querySelectorAll(".box").forEach(c=>c.classList.remove("on"));
  petEl.innerHTML = "";
};
const mask = document.getElementById("mask");
document.getElementById("sync").onclick = ()=>mask.classList.add("on");
document.getElementById("close").onclick = ()=>mask.classList.remove("on");
mask.onclick = e=>{if(e.target===mask) mask.classList.remove("on");};

showStep(0);
renderPets(D.boxes[0]);
