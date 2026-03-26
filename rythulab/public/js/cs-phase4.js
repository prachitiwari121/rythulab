/* ═══ Phase 4: System Evaluation & Layout Transfer ════════════ */
function cs_phase4_init(){
    var root=document.getElementById("cs-root"); if(!root) return;
    root.innerHTML="";
    root.appendChild(_p4_phaseTabs());
    var content=document.createElement("div");
    content.innerHTML=p4_build();
    root.appendChild(content);
}
function _p4_phaseTabs(){
    var phases=[{n:1,l:"Main crop selection"},{n:2,l:"Associate crops"},{n:3,l:"Biodiversity crops"},{n:4,l:"System evaluation"}];
    var d=document.createElement("div"); d.className="cs-ptabs";
    d.innerHTML=phases.map(function(p){
        return'<button class="cs-ptab '+(p.n===4?"active":"") +'" onclick="cs_switchPhase('+p.n+')">'+
            '<span class="cs-pnum">'+p.n+'</span>Phase '+p.n+': '+p.l+'</button>';
    }).join("");
    return d;
}
function p4_build(){
    var mc=cs_full?cs_full():[];
    var assocCount=(CS2&&CS2.selectedAssoc?CS2.selectedAssoc.length:0)+(CS2&&CS2.selectedBorder?CS2.selectedBorder.length:0)+(CS2&&CS2.selectedTrap?CS2.selectedTrap.length:0);
    var bdCount=CS3&&CS3.selected?CS3.selected.length:0;
    var totalCrops=mc.length+assocCount+bdCount;

    // Score: 0–100 across 5 dimensions
    function score(val,max){return Math.min(100,Math.round((val/max)*100));}
    var scores={
        water:    CS2&&CS2.mainCrops?Math.min(100,Math.round((CS_FARM.wa/(CS.wc?CS.wc.req:400))*100)):50,
        nitrogen: Math.min(100,Math.round((parseFloat(CS_FARM.cf.N.val)/350)*100)),
        pest:     Math.max(0,100-((2-CS_FARM.cf.PP.s)*25)),
        biodiv:   Math.min(100,score(totalCrops,12)*0.6+score(bdCount,5)*0.4),
        soil:     Math.round([CS_FARM.cf.SOC.s,CS_FARM.cf.BD.s,CS_FARM.cf.DR.s,CS_FARM.cf.ER.s].reduce(function(a,b){return a+b;},0)/4*20)
    };
    var overall=Math.round((scores.water+scores.nitrogen+scores.pest+scores.biodiv+scores.soil)/5);
    function bar(val){
        var c=val>=70?"var(--csg400)":val>=40?"var(--csa200)":"var(--csr400)";
        return'<div style="flex:1;background:#ccdcc0;border-radius:3px;height:14px;overflow:hidden">'+
            '<div style="width:'+val+'%;height:100%;background:'+c+';border-radius:3px"></div></div>';
    }
    function scoreRow(label,val,note){
        return'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'+
            '<span style="font-size:12px;font-weight:700;color:var(--text-dark);min-width:160px">'+label+'</span>'+
            bar(val)+
            '<span style="font-size:13px;font-weight:700;color:'+(val>=70?"var(--csg600)":val>=40?"var(--csa600)":"var(--csr600)")+'">'+val+'</span>'+
            '<span style="font-size:11px;color:#3a4a2a;min-width:100px">'+note+'</span></div>';
    }
    // Full crop list for layout transfer
    var allCropRows=mc.map(function(c){return'<tr><td style="font-weight:700;color:var(--text-dark)">'+c.name+'</td><td style="color:#3a4a2a">Main crop</td><td>'+c.a.toFixed(1)+' ha</td></tr>';}).join("")+
        (CS2&&CS2.selectedAssoc?CS2.selectedAssoc.map(function(id){var e=(CS2.associateList||[]).find(function(x){return x.crop.id===id;});return e?'<tr><td style="font-weight:700;color:var(--text-dark)">'+e.crop.name+'</td><td style="color:var(--csg600)">Associate</td><td>—</td></tr>':"";}).join(""):"")+(CS2&&CS2.selectedBorder?CS2.selectedBorder.map(function(id){var e=(CS2.borderList||[]).find(function(x){return x.crop.id===id;});return e?'<tr><td style="font-weight:700;color:var(--text-dark)">'+e.crop.name+'</td><td style="color:var(--csa600)">Border</td><td>—</td></tr>':"";}).join(""):"")+(CS2&&CS2.selectedTrap?CS2.selectedTrap.map(function(id){var e=(CS2.trapList||[]).find(function(x){return x.crop.id===id;});return e?'<tr><td style="font-weight:700;color:var(--text-dark)">'+e.crop.name+'</td><td style="color:var(--csr600)">Trap</td><td>—</td></tr>':"";}).join(""):"")+(CS3&&CS3.selected?CS3.selected.map(function(id){var e=(CS3.recommendations||[]).find(function(x){return x.crop.id===id;});return e?'<tr><td style="font-weight:700;color:var(--text-dark)">'+e.crop.name+'</td><td style="color:#7b3fa0">Biodiversity</td><td>—</td></tr>':"";}).join(""):"");

return'<div class="cs-sc">'+
        '<div class="cs-bdg"><span class="cs-bdg-n">Phase 4</span><span class="cs-bdg-t">System evaluation & layout transfer</span></div>'+
        '<div class="cs-ttl">System evaluation scores</div>'+'<div class="cs-desc">Summarizes how well the crop system performs in terms of feasibility, resource use, and ecological balance. <span style="color:red;">[Please Note: The following data is yet to be finalized and is provided for illustrative purposes only.]</span></div>'+'<hr class="cs-hr">'+
        '<div class="cs-scards" style="grid-template-columns:repeat(5,1fr)">'+
        '<div class="cs-sc2"><div class="cs-sc2-n '+(mc.length>0?"sn-g":"sn-r")+'">'+mc.length+'</div><div class="cs-sc2-l">main crops</div></div>'+
        '<div class="cs-sc2"><div class="cs-sc2-n sn-g">'+assocCount+'</div><div class="cs-sc2-l">associate crops</div></div>'+
        '<div class="cs-sc2"><div class="cs-sc2-n sn-g">'+bdCount+'</div><div class="cs-sc2-l">biodiversity crops</div></div>'+
        '<div class="cs-sc2"><div class="cs-sc2-n sn-g">'+totalCrops+'</div><div class="cs-sc2-l">total crops</div></div>'+
        '<div class="cs-sc2"><div class="cs-sc2-n '+(overall>=70?"sn-g":overall>=40?"sn-w":"sn-r")+'">'+overall+'</div><div class="cs-sc2-l">overall score</div></div>'+
        '</div>'+
        '<div class="cs-fcrd" style="margin-bottom:12px"><div class="cs-fcht">System evaluation scores</div>'+
        scoreRow("Water Feasibility",    scores.water,  scores.water>=70?"Good":"Needs attention")+
        scoreRow("Nitrogen Availability",scores.nitrogen,scores.nitrogen>=70?"Good":"Supplement needed")+
        scoreRow("Pest Resilience",      scores.pest,   scores.pest>=70?"Good":"High pest risk")+
        scoreRow("Biodiversity Index",   scores.biodiv, scores.biodiv>=70?"Good":"Low diversity")+
        scoreRow("Soil Health",          scores.soil,   scores.soil>=70?"Good":"Soil improvement needed")+
        '</div>'+
        '<div class="cs-fcrd" style="margin-bottom:12px"><div class="cs-fcht">Final confirmed crop list</div>'+
        '<div style="overflow-x:auto"><table class="cs-dtbl"><thead><tr><th>Crop</th><th>Role</th><th>Area</th></tr></thead>'+
        '<tbody>'+allCropRows+'</tbody></table></div></div>'+
        '<div class="cs-vcrd cs-vc-ok"><div class="cs-vci cs-vci-ok">✓</div>'+
        '<div><div class="cs-vttl">Crop system finalised — ready for layout design</div>'+
        '<div class="cs-vmsg">Your complete crop list has been confirmed across all 4 phases. Transfer to the layout builder to design your field.</div>'+
        '</div></div>'+
        '<div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">'+
        '<button class="cs-btn sec" onclick="cs_switchPhase(3)">← Back to Phase 3</button>'+
        '<button class="cs-btn pri" onclick="p4_transferToLayout()">🌿 Transfer to Layout Builder →</button>'+
        '</div></div>';
}
function p4_transferToLayout(){
    var mc=cs_full?cs_full():[];
    // Store confirmed list for layout builder
    window._confirmedCrops={main:mc,assoc:CS2&&CS2.selectedAssoc?CS2.selectedAssoc:[],border:CS2&&CS2.selectedBorder?CS2.selectedBorder:[],trap:CS2&&CS2.selectedTrap?CS2.selectedTrap:[],bio:CS3&&CS3.selected?CS3.selected:[]};
    // Open layout builder
    if(typeof openBuilder==="function") openBuilder(null);
    else window.location.href="/field-planner";
}
