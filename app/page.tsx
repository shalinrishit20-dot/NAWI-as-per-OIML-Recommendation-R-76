'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { Activity, Archive, ArrowRight, Camera, Check, CheckCircle2, ChevronDown, ChevronRight, ClipboardCheck, Download, FileCheck2, FlaskConical, Gauge, History, LayoutDashboard, LogOut, Menu, PackageSearch, Play, Plus, Printer, ScanSearch, Scale, Search, ShieldCheck, Square, Upload, Video, X } from 'lucide-react';

type View = 'dashboard'|'instruments'|'evaluation'|'reports'|'live'|'manufacturer'|'visual'|'verify'|'audit';
type NavigationLocation = {view:View;reportId:number|null};
const views:View[]=['dashboard','instruments','evaluation','reports','live','manufacturer','visual','verify','audit'];
function isView(value:string|null):value is View{return value!==null&&views.includes(value as View)}
function normaliseNavigationLocation(view:View,reportId:number|null):NavigationLocation{
 const validReportId=typeof reportId==='number'&&Number.isSafeInteger(reportId)&&reportId>0;
 return {view,reportId:view==='evaluation'&&validReportId?reportId:null};
}
function readNavigationLocation():NavigationLocation{
 const params=new URLSearchParams(window.location.search);
 const view=isView(params.get('view'))?params.get('view') as View:'dashboard';
 const rawReportId=params.get('report');
 const reportId=rawReportId!==null&&/^[1-9]\d*$/.test(rawReportId)?Number(rawReportId):null;
 return normaliseNavigationLocation(view,reportId);
}
function navigationUrl(location:NavigationLocation){
 const url=new URL(window.location.href);
 if(location.view==='dashboard')url.searchParams.delete('view');else url.searchParams.set('view',location.view);
 if(location.view==='evaluation'&&location.reportId!==null)url.searchParams.set('report',String(location.reportId));else url.searchParams.delete('report');
 return `${url.pathname}${url.search}${url.hash}`;
}
function currentNavigationUrl(){return `${window.location.pathname}${window.location.search}${window.location.hash}`}
function normaliseScrollY(value:unknown){return typeof value==='number'&&Number.isFinite(value)&&value>=0?value:0}
function navigationScrollY(state:unknown){
 if(!state||typeof state!=='object'||(state as {nawiLabNavigation?:unknown}).nawiLabNavigation!==true)return 0;
 return normaliseScrollY((state as {scrollY?:unknown}).scrollY);
}
function navigationHistoryState(location:NavigationLocation,scrollY:number){return {nawiLabNavigation:true,view:location.view,reportId:location.reportId,scrollY:normaliseScrollY(scrollY)}}
function saveCurrentNavigationScroll(){
 const location=readNavigationLocation();
 window.history.replaceState(navigationHistoryState(location,window.scrollY),'',navigationUrl(location));
}
type User = {id:number; username:string; role:string};
function canAccessView(role:string,location:NavigationLocation){
 if(role==='Admin')return true;
 if(role==='Tester')return location.view!=='manufacturer'&&location.view!=='audit';
 if(role==='Reviewer')return location.view==='dashboard'||location.view==='instruments'||location.view==='reports'||location.view==='visual'||location.view==='verify'||(location.view==='evaluation'&&location.reportId!==null);
 if(role==='Manufacturer')return location.view==='dashboard'||location.view==='instruments'||location.view==='manufacturer'||location.view==='visual'||location.view==='verify';
 return false;
}
type Instrument = {id:number; manufacturer:string; model:string; serial_number:string; accuracy_class:string; max_capacity:number; min_capacity:number; e:number; d:number; unit:string; software_version?:string; images:string[]};
type ObservationCalculation = {
  standard_code:string; standard_edition:string; ruleset_version:string;
  accuracy_class:string; verification_stage:string;
  canonical_load:number; verification_scale_interval:number; actual_scale_interval:number;
  rounding_elimination_required:boolean; error_method:string; additional_load:number|null;
  indication_before_rounding:number; error_before_rounding:number; zero_error:number;
  corrected_error:number; absolute_corrected_error:number;
  mpe_multiplier:number; mpe:number; margin_to_limit:number;
  error_rule_reference:string; mpe_rule_reference:string;
};
type Observation = {
  id:number; test_type:string; position?:string; applied_load:number; reference_value:number;
  indication:number; error:number; mpe:number; result:string; notes?:string;
  calculation:ObservationCalculation|null;
};
type TareWeighingObs = {
  net_load:number; gross_load:number; load:number; indication:number; additional_load:number|null;
  indication_before_rounding:number; error_before_rounding:number; zero_error:number;
  corrected_error:number; absolute_corrected_error:number; mpe:number; margin_to_limit:number;
  result:string; error_method:string; ruleset_version:string; error_rule_reference:string; mpe_rule_reference:string
};
type TareWeighingTest = {
  id:number; tare_value:number; accuracy_class:string; maximum_capacity:number; minimum_capacity:number;
  verification_scale_interval:number; actual_scale_interval:number; unit:string;
  required_observations:number; observation_count:number; complete:boolean; status:string;
  failed_observation_indices:number[]; observations:TareWeighingObs[];
  standard_code:string; standard_edition:string; ruleset_version:string; rule_reference:string
};
type ZeroSettingTest = {
  id:number; setting_mode:string; indication:number; additional_load:number|null;
  verification_scale_interval:number; actual_scale_interval:number; unit:string;
  rounding_elimination_required:boolean; error_method:string;
  indication_before_rounding:number; zero_error:number; absolute_zero_error:number;
  permitted_limit:number; margin_to_limit:number; status:string;
  standard_code:string; standard_edition:string; ruleset_version:string; rule_reference:string
};
type RepeatabilityTest = {
  id:number; series_role:string; accuracy_class:string; max_capacity:number; applied_load:number;
  verification_scale_interval:number; unit:string; readings:number[];
  weighing_count:number; required_weighings:number; minimum_result:number; maximum_result:number;
  spread:number; mpe:number; complete:boolean; spread_within_mpe:boolean; status:string;
  standard_code:string; standard_edition:string; ruleset_version:string; rule_reference:string;
};
type EccentricityTest = {
  id:number; accuracy_class:string; max_capacity:number; verification_scale_interval:number; unit:string;
  maximum_additive_tare_effect:number; required_test_load:number;
  required_positions:string[]; tested_positions:string[];
  position_errors:Record<string, number>; failed_positions:string[];
  mpe:number; complete:boolean; all_positions_within_mpe:boolean; status:string;
  standard_code:string; standard_edition:string; ruleset_version:string; rule_reference:string;
};
type CoreTestProgramme = {
  standard_code:string; standard_edition:string; ruleset_version:string;
  scope_name:string; scope_note:string; full_standard_coverage:boolean;
  observation_status:string; repeatability_status:string; eccentricity_status:string;
  zero_setting_status:string; tare_weighing_status:string; overall_status:string;
  failed_modules:string[]; incomplete_modules:string[];
  observation_count:number;
  repeatability_half_max_status:string|null; repeatability_near_max_status:string|null;
  rule_references:string[];
  legacy_observation_count:number; observation_snapshots_complete:boolean;
};
type Report = {id:number; report_number:string; status:string; final_result:string; standard_name:string; standard_version:string; laboratory?:string; location?:string; temperature?:number; humidity?:number; pressure?:number; created_at:string; instrument:Instrument; observations:Observation[]; evidence:any[]; repeatability?:{half_max:RepeatabilityTest|null; near_max:RepeatabilityTest|null}; eccentricity?:EccentricityTest|null; zero_setting?:ZeroSettingTest|null; tare_weighing?:TareWeighingTest|null; test_programme?:CoreTestProgramme};
function roundingRequiredFor(inst:{e:number;d:number}){return Number(inst.d)>0.2*Number(inst.e)}
function finiteNumber(raw:string){if(raw===''||raw===undefined||raw===null)return null;const n=Number(raw);return Number.isFinite(n)?n:null}
function CalculationPanel({obs,unit}:{obs:Observation;unit:string}){
  const c=obs.calculation;
  if(!c)return <div className="warning calc-panel"><ShieldCheck/><div><b>Legacy observation</b><p>No verified calculation snapshot. Error {obs.error} {unit} · MPE ±{obs.mpe} {unit} · {obs.result}</p></div></div>;
  const method=c.error_method==='changeover_point'?'Changeover point':'Direct';
  return <div className="warning calc-panel"><ShieldCheck/><div>
    <b>Verified calculation</b>
    <dl className="calc-grid">
      <div><dt>Method</dt><dd>{method}</dd></div>
      <div><dt>P / Indication before rounding</dt><dd>{c.indication_before_rounding} {unit}</dd></div>
      <div><dt>E / Error before rounding</dt><dd>{c.error_before_rounding} {unit}</dd></div>
      <div><dt>E0 / Zero error</dt><dd>{c.zero_error} {unit}</dd></div>
      <div><dt>Ec / Corrected error</dt><dd>{c.corrected_error} {unit}</dd></div>
      <div><dt>MPE</dt><dd>±{c.mpe} {unit}</dd></div>
      <div><dt>Margin to limit</dt><dd>{c.margin_to_limit} {unit}</dd></div>
      <div><dt>Result</dt><dd>{obs.result}</dd></div>
      <div><dt>Ruleset</dt><dd>{c.ruleset_version}</dd></div>
    </dl>
    <p className="rule-refs">{c.error_rule_reference}<br/>{c.mpe_rule_reference}</p>
  </div></div>;
}


type InstrumentClassification = {
  standard_code:string; standard_edition:string; ruleset_version:string; rule_reference:string;
  accuracy_class:string;
  max_capacity:number; min_capacity:number; verification_scale_interval:number; actual_scale_interval:number; unit:string;
  number_of_verification_intervals:number; minimum_n:number|null; maximum_n:number|null;
  minimum_capacity_multiplier:number|null; minimum_capacity_required:number|null; minimum_capacity_in_d:number|null;
  valid:boolean; errors:string[];
};
type ApiErrorBody = { error?: string; detail?: string; classification?: InstrumentClassification };
class ApiRequestError extends Error {
  status:number;
  body:ApiErrorBody;
  constructor(message:string, status:number, body:ApiErrorBody){
    super(message);
    this.name='ApiRequestError';
    this.status=status;
    this.body=body;
  }
}
const api = async <T = any>(url: string, opt: RequestInit = {}): Promise<T> => {
  const r = await fetch(url, { credentials: 'include', ...opt });
  const ct = r.headers.get('content-type') || '';
  const data: any = ct.includes('application/json') ? await r.json() : await r.text();
  if (!r.ok) {
    const body: ApiErrorBody = data && typeof data === 'object' ? data : {};
    const msg = body.error
      ? body.detail ? `${body.error}: ${body.detail}` : body.error
      : typeof data === 'string' && data ? data : 'Request failed';
    throw new ApiRequestError(msg, r.status, body);
  }
  return data as T;
};
const post=(url:string,data:any)=>api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});

const put=(url:string,data:any)=>api(url,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
function parseReadings(raw:string){
  const parts=raw.split(/[\s,;]+/).map(s=>s.trim()).filter(Boolean);
  if(!parts.length) return {ok:false as const, error:'Enter at least one reading'};
  const nums:number[]=[];
  for(const p of parts){
    const n=Number(p);
    if(!Number.isFinite(n)) return {ok:false as const, error:`Malformed reading: ${p}`};
    nums.push(n);
  }
  return {ok:true as const, readings:nums};
}
function StatusPill({text}:{text:string}){
  const tone=text==='PASS'?'green':text==='FAIL'?'red':text==='INCOMPLETE'?'blue':'yellow';
  return <Pill tone={tone}>{text}</Pill>;
}

function programmeProgress(prog?:CoreTestProgramme|null){if(!prog)return 0;const done=(s:string)=>s==='PASS'||s==='FAIL';let n=0;if(done(prog.zero_setting_status))n++;if(done(prog.observation_status))n++;if(done(prog.eccentricity_status))n++;if(done(prog.repeatability_status))n++;if(done(prog.tare_weighing_status))n++;return n===0?0:[0,20,40,60,80,100][n];}
function workflowLabel(status:string){
  if(status==='Review') return 'Submitted for Review';
  if(status==='Completed') return 'Approved';
  return 'Draft';
}
function WorkflowPanel({report,user,onReload,onError}:{report:Report;user:User;onReload:()=>Promise<void>;onError:(m:string)=>void}){
  const prog=report.test_programme;
  const overall=prog?.overall_status||'INCOMPLETE';
  const editable=report.status==='In Progress';
  const canSubmit=(user.role==='Admin'||user.role==='Tester')&&editable;
  const canApprove=(user.role==='Admin'||user.role==='Reviewer') && report.status==='Review';
  const incomplete=overall==='INCOMPLETE';
  const [busy,setBusy]=useState(false);
  const submit=async()=>{
    if(!canSubmit||incomplete||busy)return;
    try{
      setBusy(true); onError('');
      await post(`/api/reports/${report.id}/complete`,{});
      await onReload();
    }catch(x:any){onError(x.message)} finally{setBusy(false)}
  };
  const approve=async()=>{
    if(!canApprove||busy)return;
    try{
      setBusy(true); onError('');
      await post(`/api/reports/${report.id}/approve`,{});
      await onReload();
    }catch(x:any){onError(x.message)} finally{setBusy(false)}
  };
  return <div className="workflow-panel">
    <span className="eyebrow">REPORT WORKFLOW</span>
    <div className="workflow-steps">
      <span className={report.status==='In Progress'?'wf-step on':report.status!=='In Progress'?'wf-step done':'wf-step'}>Draft</span>
      <span className="wf-arrow">→</span>
      <span className={report.status==='Review'?'wf-step on':report.status==='Completed'?'wf-step done':'wf-step'}>Submitted for Review</span>
      <span className="wf-arrow">→</span>
      <span className={report.status==='Completed'?'wf-step on':'wf-step'}>Approved</span>
    </div>
    <dl className="calc-grid">
      <div><dt>Technical result</dt><dd><StatusPill text={report.final_result==='PENDING'?(overall||'PENDING'):report.final_result}/></dd></div>
      <div><dt>Workflow</dt><dd><StatusPill text={workflowLabel(report.status)}/></dd></div>
    </dl>
    {report.status==='In Progress'&&incomplete&&<p className="method-note">Submit is unavailable until implemented-core modules are complete{prog?.incomplete_modules?.length?`: ${prog.incomplete_modules.join(', ')}`:'.'}</p>}
    {report.status==='In Progress'&&overall==='FAIL'&&<p className="method-note">This report contains failed implemented-core tests and can still be submitted for review.</p>}
    {report.status==='Review'&&<p className="method-note">Test data is locked while the report is under review.</p>}
    {report.status==='Completed'&&<p className="method-note">Workflow approval recorded. Technical result remains PASS/FAIL for the implemented OIML R76 core scope.</p>}
    <div className="form-actions" style={{marginTop:12}}>
      {canSubmit&&<button type="button" className="primary" disabled={incomplete||busy} onClick={submit}>Submit for Review <ArrowRight/></button>}
      {canApprove&&<button type="button" className="primary" disabled={busy} onClick={approve}>Approve Report</button>}
    </div>
  </div>;
}
function ProgrammePanel({prog}:{prog:CoreTestProgramme}){
  return <div className="programme-panel">
    <span className="eyebrow">CORE TEST PROGRAMME</span>
    <div className="programme-head"><h3>{prog.scope_name}</h3><StatusPill text={prog.overall_status}/></div>
    <p className="scope-note">{prog.scope_note}</p>
    <p className="scope-note strong">Implemented core scope only — not a complete OIML R76 type-evaluation verdict.</p>
    <dl className="calc-grid">
      <div><dt>Zero-setting</dt><dd><StatusPill text={prog.zero_setting_status}/></dd></div>
      <div><dt>Weighing performance</dt><dd><StatusPill text={prog.observation_status}/></dd></div>
      <div><dt>Eccentric loading</dt><dd><StatusPill text={prog.eccentricity_status}/></dd></div>
      <div><dt>Repeatability</dt><dd><StatusPill text={prog.repeatability_status}/></dd></div>
      <div><dt>Tare weighing</dt><dd><StatusPill text={prog.tare_weighing_status}/></dd></div>
      <div><dt>Half-Max</dt><dd>{prog.repeatability_half_max_status||'—'}</dd></div>
      <div><dt>Near-Max</dt><dd>{prog.repeatability_near_max_status||'—'}</dd></div>
      <div><dt>Ruleset</dt><dd>{prog.ruleset_version}</dd></div>
    </dl>
    <p className="method-note">Failed: {prog.failed_modules.length?prog.failed_modules.join(', '):'none'} · Incomplete: {prog.incomplete_modules.length?prog.incomplete_modules.join(', '):'none'}</p>
    {prog.legacy_observation_count>0&&<p className="method-note">Legacy observations without calculation snapshots: {prog.legacy_observation_count}. Observation status cannot pass until those rows have verified snapshots.</p>}
  </div>;
}
function RepeatabilityCard({reportId,title,role,unit,snapshot,reload,disabled}:{reportId:number;title:string;role:'half_max'|'near_max';unit:string;snapshot:RepeatabilityTest|null;reload:()=>Promise<void>;disabled?:boolean}){
  const [load,setLoad]=useState('');
  const [text,setText]=useState('');
  const [err,setErr]=useState('');
  const save=async(e:any)=>{
    e.preventDefault();
    if(disabled)return;
    const applied=finiteNumber(load);
    if(applied===null){setErr('Applied load is required');return}
    const parsed=parseReadings(text);
    if(!parsed.ok){setErr(parsed.error);return}
    try{
      setErr('');
      await put(`/api/reports/${reportId}/repeatability/${role}`,{applied_load:applied,readings:parsed.readings});
      setLoad('');setText('');
      await reload();
    }catch(x:any){setErr(x.message)}
  };
  return <div className="module-card">
    <div className="module-card-head"><h3>{title}</h3>{snapshot&&<StatusPill text={snapshot.status}/>}</div>
    <form className={"mini-form"+(disabled?" is-locked":"")} onSubmit={save}>
      <label>Applied load ({unit})<input type="number" step="any" value={load} onChange={e=>setLoad(e.target.value)} disabled={disabled}/></label>
      <label>Readings (one per line or comma-separated)<textarea rows={4} value={text} onChange={e=>setText(e.target.value)} placeholder="15&#10;15.001&#10;14.999" disabled={disabled}/></label>
      {err&&<p className="error">{err}</p>}
      <button className="primary" disabled={disabled}>Save series</button>
    </form>
    {snapshot&&<dl className="calc-grid">
      <div><dt>Applied load</dt><dd>{snapshot.applied_load} {snapshot.unit}</dd></div>
      <div><dt>Weighings</dt><dd>{snapshot.weighing_count} / {snapshot.required_weighings}</dd></div>
      <div><dt>Min / Max</dt><dd>{snapshot.minimum_result} / {snapshot.maximum_result}</dd></div>
      <div><dt>Spread</dt><dd>{snapshot.spread}</dd></div>
      <div><dt>MPE</dt><dd>±{snapshot.mpe}</dd></div>
      <div><dt>Ruleset</dt><dd>{snapshot.ruleset_version}</dd></div>
    </dl>}
    {snapshot&&<p className="rule-refs">{snapshot.rule_reference}</p>}
  </div>;
}


function emptyTareRow(){return {net_load:'',reference_value:'',indication:'',zero_error:'',additional_load:''}}
function TareWeighingCard({reportId,unit,snapshot,roundingRequired,reload,disabled}:{reportId:number;unit:string;snapshot:TareWeighingTest|null;roundingRequired:boolean;reload:()=>Promise<void>;disabled?:boolean}){
  const [tare,setTare]=useState(snapshot!=null?String(snapshot.tare_value):'0');
  const [rows,setRows]=useState(()=>[emptyTareRow(),emptyTareRow(),emptyTareRow(),emptyTareRow(),emptyTareRow()]);
  const [err,setErr]=useState('');
  const setCell=(i:number,key:string,val:string)=>setRows(rs=>rs.map((r,idx)=>idx===i?{...r,[key]:val}:r));
  const save=async(e:any)=>{
    e.preventDefault();
    if(disabled)return;
    const tareN=finiteNumber(tare);
    if(tare===''||tareN===null){setErr('Tare value is required (use 0 if none)');return}
    const observations:any[]=[];
    for(let i=0;i<rows.length;i++){
      const r=rows[i];
      const blank=!r.net_load&&!r.reference_value&&!r.indication&&!r.zero_error&&!r.additional_load;
      if(blank) continue;
      const net=finiteNumber(r.net_load), L=finiteNumber(r.reference_value), I=finiteNumber(r.indication), E0=finiteNumber(r.zero_error);
      if(net===null){setErr(`Observation ${i+1}: net load is required`);return}
      if(L===null){setErr(`Observation ${i+1}: reference value is required`);return}
      if(I===null){setErr(`Observation ${i+1}: indication is required`);return}
      if(r.zero_error===''||E0===null){setErr(`Observation ${i+1}: zero error is required`);return}
      const item:any={net_load:net,reference_value:L,indication:I,zero_error:E0};
      if(roundingRequired){
        const dL=finiteNumber(r.additional_load);
        if(r.additional_load===''||dL===null){setErr(`Observation ${i+1}: additional load ΔL is required`);return}
        item.additional_load=dL;
      }
      observations.push(item);
    }
    if(!observations.length){setErr('Enter at least one tare-weighing observation');return}
    try{
      setErr('');
      await put(`/api/reports/${reportId}/tare-weighing`,{tare_value:tareN,observations});
      await reload();
    }catch(x:any){setErr(x.message)}
  };
  return <div className="module-card fullrow">
    <div className="module-card-head"><h3>Tare weighing</h3>{snapshot&&<StatusPill text={snapshot.status}/>}</div>
    <p className="method-note">Subtractive tare weighing using a fixed tare value and net-load observations. At least 5 observations are required for a complete series. Results come from the backend snapshot.</p>
    <form className={"mini-form"+(disabled?" is-locked":"")} onSubmit={save}>
      <label>Tare value ({unit})<input type="number" step="any" value={tare} onChange={e=>setTare(e.target.value)} disabled={disabled}/></label>
      <div className="tare-obs-list">
        {rows.map((r,i)=><div className="tare-obs-row" key={i}>
          <b>Observation {i+1}</b>
          <div className="fields obs-fields">
            <label>Net load<span><input type="number" step="any" value={r.net_load} onChange={e=>setCell(i,'net_load',e.target.value)} disabled={disabled}/><i>{unit}</i></span></label>
            <label>Reference L<span><input type="number" step="any" value={r.reference_value} onChange={e=>setCell(i,'reference_value',e.target.value)} disabled={disabled}/><i>{unit}</i></span></label>
            <label>Indication I<span><input type="number" step="any" value={r.indication} onChange={e=>setCell(i,'indication',e.target.value)} disabled={disabled}/><i>{unit}</i></span></label>
            <label>Zero error E0<span><input type="number" step="any" value={r.zero_error} onChange={e=>setCell(i,'zero_error',e.target.value)} disabled={disabled}/><i>{unit}</i></span></label>
            {roundingRequired&&<label>Additional load ΔL<span><input type="number" step="any" value={r.additional_load} onChange={e=>setCell(i,'additional_load',e.target.value)} disabled={disabled}/><i>{unit}</i></span></label>}
          </div>
        </div>)}
      </div>
      <button type="button" className="outline" disabled={disabled} onClick={()=>setRows(rs=>[...rs,emptyTareRow()])}>Add observation</button>
      {err&&<p className="error">{err}</p>}
      <button className="primary" disabled={disabled}>Save tare weighing</button>
    </form>
    {snapshot&&<>
      <dl className="calc-grid">
        <div><dt>Status</dt><dd><StatusPill text={snapshot.status}/></dd></div>
        <div><dt>Tare value</dt><dd>{snapshot.tare_value} {snapshot.unit}</dd></div>
        <div><dt>Observation count</dt><dd>{snapshot.observation_count}</dd></div>
        <div><dt>Required observations</dt><dd>{snapshot.required_observations}</dd></div>
        <div><dt>Complete</dt><dd>{snapshot.complete?'Yes':'No'}</dd></div>
        <div><dt>Failed indices</dt><dd>{snapshot.failed_observation_indices.length?snapshot.failed_observation_indices.join(', '):'none'}</dd></div>
        <div><dt>Ruleset</dt><dd>{snapshot.ruleset_version}</dd></div>
        <div><dt>Rule reference</dt><dd>{snapshot.rule_reference}</dd></div>
      </dl>
      {snapshot.observations.map((o,i)=><dl className="calc-grid" key={i}>
        <div><dt>Obs {i+1} result</dt><dd><StatusPill text={o.result}/></dd></div>
        <div><dt>Net / Gross</dt><dd>{o.net_load} / {o.gross_load} {snapshot.unit}</dd></div>
        <div><dt>L / I</dt><dd>{o.load} / {o.indication} {snapshot.unit}</dd></div>
        <div><dt>ΔL</dt><dd>{o.additional_load==null?'—':`${o.additional_load} ${snapshot.unit}`}</dd></div>
        <div><dt>P</dt><dd>{o.indication_before_rounding} {snapshot.unit}</dd></div>
        <div><dt>E / E0 / Ec</dt><dd>{o.error_before_rounding} / {o.zero_error} / {o.corrected_error}</dd></div>
        <div><dt>|Ec| / MPE / Margin</dt><dd>{o.absolute_corrected_error} / {o.mpe} / {o.margin_to_limit}</dd></div>
        <div><dt>Method</dt><dd>{o.error_method}</dd></div>
        <div><dt>Error ref</dt><dd>{o.error_rule_reference}</dd></div>
        <div><dt>MPE ref</dt><dd>{o.mpe_rule_reference}</dd></div>
      </dl>)}
    </>}
  </div>;
}
function ZeroSettingCard({reportId,unit,snapshot,roundingRequired,reload,disabled}:{reportId:number;unit:string;snapshot:ZeroSettingTest|null;roundingRequired:boolean;reload:()=>Promise<void>;disabled?:boolean}){
  const [mode,setMode]=useState(snapshot?.setting_mode||'non_automatic');
  const [indication,setIndication]=useState(snapshot!=null?String(snapshot.indication):'');
  const [delta,setDelta]=useState(snapshot?.additional_load!=null?String(snapshot.additional_load):'');
  const [err,setErr]=useState('');
  const save=async(e:any)=>{
    e.preventDefault();
    if(disabled)return;
    const I=finiteNumber(indication);
    if(I===null){setErr('Indication I is required');return}
    const payload:any={setting_mode:mode,indication:I};
    if(roundingRequired){
      const dL=finiteNumber(delta);
      if(delta===''||dL===null){setErr('Additional load ΔL is required for this instrument (d > 0.2 e)');return}
      payload.additional_load=dL;
    }
    try{
      setErr('');
      await put(`/api/reports/${reportId}/zero-setting`,payload);
      await reload();
    }catch(x:any){setErr(x.message)}
  };
  return <div className="module-card fullrow">
    <div className="module-card-head"><h3>Zero-setting accuracy</h3>{snapshot&&<StatusPill text={snapshot.status}/>}</div>
    <p className="method-note">Zero-setting accuracy evaluates post-zero-setting deviation only. This is not complete §4.5 zero-setting-device compliance.</p>
    <form className={"mini-form"+(disabled?" is-locked":"")} onSubmit={save}>
      <label>Setting mode<select value={mode} onChange={e=>setMode(e.target.value)} disabled={disabled}>
        <option value="non_automatic">Non-automatic</option>
        <option value="semi_automatic">Semi-automatic</option>
      </select></label>
      <label>Indication I ({unit})<input type="number" step="any" value={indication} onChange={e=>setIndication(e.target.value)} disabled={disabled}/></label>
      {roundingRequired&&<label>Additional load ΔL ({unit})<input type="number" step="any" value={delta} onChange={e=>setDelta(e.target.value)} disabled={disabled}/></label>}
      {err&&<p className="error">{err}</p>}
      <button className="primary" disabled={disabled}>Save zero-setting</button>
    </form>
    {snapshot&&<dl className="calc-grid">
      <div><dt>Status</dt><dd><StatusPill text={snapshot.status}/></dd></div>
      <div><dt>Setting mode</dt><dd>{snapshot.setting_mode}</dd></div>
      <div><dt>Indication I</dt><dd>{snapshot.indication} {snapshot.unit}</dd></div>
      <div><dt>Additional load ΔL</dt><dd>{snapshot.additional_load==null?'—' : `${snapshot.additional_load} ${snapshot.unit}`}</dd></div>
      <div><dt>Error method</dt><dd>{snapshot.error_method}</dd></div>
      <div><dt>P / indication before rounding</dt><dd>{snapshot.indication_before_rounding} {snapshot.unit}</dd></div>
      <div><dt>Zero error</dt><dd>{snapshot.zero_error} {snapshot.unit}</dd></div>
      <div><dt>|Zero error|</dt><dd>{snapshot.absolute_zero_error} {snapshot.unit}</dd></div>
      <div><dt>Permitted limit</dt><dd>{snapshot.permitted_limit} {snapshot.unit}</dd></div>
      <div><dt>Margin to limit</dt><dd>{snapshot.margin_to_limit} {snapshot.unit}</dd></div>
      <div><dt>e</dt><dd>{snapshot.verification_scale_interval} {snapshot.unit}</dd></div>
      <div><dt>d</dt><dd>{snapshot.actual_scale_interval} {snapshot.unit}</dd></div>
      <div><dt>Ruleset</dt><dd>{snapshot.ruleset_version}</dd></div>
      <div><dt>Rule reference</dt><dd>{snapshot.rule_reference}</dd></div>
    </dl>}
  </div>;
}
function EccentricityCard({reportId,unit,snapshot,reload,disabled}:{reportId:number;unit:string;snapshot:EccentricityTest|null;reload:()=>Promise<void>;disabled?:boolean}){
  const [tare,setTare]=useState('0');
  const [q,setQ]=useState({Q1:'',Q2:'',Q3:'',Q4:''});
  const [err,setErr]=useState('');
  const save=async(e:any)=>{
    e.preventDefault();
    if(disabled)return;
    const tareN=finiteNumber(tare);
    if(tare===''||tareN===null){setErr('Maximum additive tare effect is required (use 0 if none)');return}
    const position_errors:Record<string,number>={};
    for(const key of ['Q1','Q2','Q3','Q4'] as const){
      const raw=q[key];
      if(raw==='') continue;
      const n=finiteNumber(raw);
      if(n===null){setErr(`${key} must be a finite corrected error Ec`);return}
      position_errors[key]=n;
    }
    if(!Object.keys(position_errors).length){setErr('Enter at least one quarter corrected error Ec');return}
    try{
      setErr('');
      await put(`/api/reports/${reportId}/eccentricity`,{maximum_additive_tare_effect:tareN,position_errors});
      await reload();
    }catch(x:any){setErr(x.message)}
  };
  const pe=snapshot?.position_errors||{};
  return <div className="module-card fullrow">
    <div className="module-card-head"><h3>Eccentric loading — quarter segments</h3>{snapshot&&<StatusPill text={snapshot.status}/>}</div>
    <p className="method-note">Enter already-corrected errors Ec for each loaded quarter. Blank quarters are omitted (not sent as zero).</p>
    <form className={"mini-form"+(disabled?" is-locked":"")} onSubmit={save}>
      <label>Maximum additive tare effect ({unit})<input type="number" step="any" value={tare} onChange={e=>setTare(e.target.value)} disabled={disabled}/></label>
      <div className="fields obs-fields">
        {(['Q1','Q2','Q3','Q4'] as const).map(k=>
          <label key={k}>{k} corrected error Ec<span><input type="number" step="any" value={q[k]} onChange={e=>setQ({...q,[k]:e.target.value})} disabled={disabled}/><i>{unit}</i></span></label>
        )}
      </div>
      {err&&<p className="error">{err}</p>}
      <button className="primary" disabled={disabled}>Save eccentricity</button>
    </form>
    {snapshot&&<dl className="calc-grid">
      <div><dt>Required test load</dt><dd>{snapshot.required_test_load} {snapshot.unit}</dd></div>
      <div><dt>MPE</dt><dd>±{snapshot.mpe}</dd></div>
      <div><dt>Tested</dt><dd>{snapshot.tested_positions.join(', ')||'—'}</dd></div>
      <div><dt>Failed</dt><dd>{snapshot.failed_positions.length?snapshot.failed_positions.join(', '):'none'}</dd></div>
      {(['Q1','Q2','Q3','Q4'] as const).map(k=> k in pe ? <div key={k}><dt>{k} Ec</dt><dd>{pe[k]} {snapshot.unit}</dd></div> : null)}
      <div><dt>Ruleset</dt><dd>{snapshot.ruleset_version}</dd></div>
    </dl>}
    {snapshot&&<p className="rule-refs">{snapshot.rule_reference}</p>}
  </div>;
}

function Pill({children,tone='ink'}:{children:React.ReactNode;tone?:'ink'|'green'|'yellow'|'red'|'blue'}){return <span className={`pill pill-${tone}`}>{children}</span>}
function Badge({text}:{text:string}){const wf=text==='In Progress'||text==='Review'||text==='Completed';return <Pill tone={text==='PASS'||text==='Completed'?'green':text==='FAIL'?'red':text==='Review'?'yellow':'blue'}>{wf?workflowLabel(text):text}</Pill>}
function Result({text}:{text:string}){return <Pill tone={text==='PASS'?'green':text==='FAIL'?'red':text==='INCOMPLETE'?'blue':'yellow'}>{text}</Pill>}
function Empty({text}:{text:string}){return <div className="empty"><PackageSearch size={30}/><p>{text}</p></div>}
function Modal({title,close,children}:{title:string;close:()=>void;children:React.ReactNode}){return <div className="modal-backdrop" onClick={close}><section className="modal" onClick={e=>e.stopPropagation()}><button className="close" onClick={close}><X/></button><h2>{title}</h2>{children}</section></div>}

export default function Home(){
 const [user,setUser]=useState<User|null>(null),[demoMode,setDemoMode]=useState(false),[loading,setLoading]=useState(true),[view,setView]=useState<View>('dashboard'),[menu,setMenu]=useState(false),[navGroup,setNavGroup]=useState<string|null>(null),[notice,setNotice]=useState<any>(null),[openReportId,setOpenReportId]=useState<number|null>(null);
 useEffect(()=>{let active=true;api('/api/auth/me').then(x=>{if(!active)return;setUser(x.user);setDemoMode(x.demo_mode===true)}).catch(()=>{}).finally(()=>{if(active)setLoading(false)});return()=>{active=false}},[]);
 useEffect(()=>{
  if(!user)return;
  const previousScrollRestoration=window.history.scrollRestoration;
  window.history.scrollRestoration='manual';
  let scrollSaveFrame:number|null=null;
  let scrollRestoreFrame:number|null=null;
  const restoreNavigation=(location:NavigationLocation)=>{
   setView(location.view);setOpenReportId(location.reportId);setMenu(false);setNavGroup(null);
  };
  const allowedLocation=(location:NavigationLocation)=>canAccessView(user.role,location)?location:{view:'dashboard' as View,reportId:null};
  const onScroll=()=>{
   if(scrollSaveFrame!==null)return;
   scrollSaveFrame=window.requestAnimationFrame(()=>{
    scrollSaveFrame=null;
    saveCurrentNavigationScroll();
   });
  };
  const requestedInitialLocation=readNavigationLocation();
  const initialLocation=allowedLocation(requestedInitialLocation);
  const initialScrollY=initialLocation===requestedInitialLocation?window.scrollY:0;
  restoreNavigation(initialLocation);
  window.history.replaceState(navigationHistoryState(initialLocation,initialScrollY),'',navigationUrl(initialLocation));
  const onPopState=(event:PopStateEvent)=>{
   const requestedLocation=readNavigationLocation();
   const location=allowedLocation(requestedLocation);
   const scrollY=location===requestedLocation?navigationScrollY(event.state):0;
   flushSync(()=>restoreNavigation(location));
   const canonicalUrl=navigationUrl(location);
   if(canonicalUrl!==currentNavigationUrl())window.history.replaceState(navigationHistoryState(location,scrollY),'',canonicalUrl);
   if(scrollRestoreFrame!==null)window.cancelAnimationFrame(scrollRestoreFrame);
   scrollRestoreFrame=window.requestAnimationFrame(()=>{
    scrollRestoreFrame=null;
    window.scrollTo({top:scrollY,left:0,behavior:'auto'});
   });
  };
  window.addEventListener('scroll',onScroll,{passive:true});
  window.addEventListener('popstate',onPopState);
  return()=>{
   window.removeEventListener('scroll',onScroll);
   window.removeEventListener('popstate',onPopState);
   if(scrollSaveFrame!==null)window.cancelAnimationFrame(scrollSaveFrame);
   if(scrollRestoreFrame!==null)window.cancelAnimationFrame(scrollRestoreFrame);
   window.history.scrollRestoration=previousScrollRestoration;
  };
 },[user]);
 const replaceForbiddenReportWithOverview=useCallback(()=>{
  const location={view:'dashboard' as View,reportId:null};
  window.history.replaceState(navigationHistoryState(location,0),'',navigationUrl(location));
  setView(location.view);setOpenReportId(location.reportId);setMenu(false);setNavGroup(null);
  window.scrollTo({top:0,left:0,behavior:'auto'});
 },[]);
 if(loading)return <div className="splash"><Scale size={60}/><h1>NAWI<span> LAB.</span></h1><p>Implemented-core verification workspace</p></div>;
 if(!user)return <Login onLogin={setUser} demoMode={demoMode}/>;
 const canCreateInstrument=user.role==='Admin'||user.role==='Tester';
 const canCreateEvaluation=user.role==='Admin'||user.role==='Tester';
 const canUseLiveTest=user.role==='Admin'||user.role==='Tester';
 const canAccessReports=user.role==='Admin'||user.role==='Tester'||user.role==='Reviewer';
 const navGroups:{label:string;items:[View,string,any][]}[]=[
  {label:'Evaluation',items:[['instruments','Instruments',Scale],['evaluation','Evaluations',ClipboardCheck],['live','Live Test',Video]]},
  {label:'Records',items:[['reports','Reports',FileCheck2],['manufacturer','Manufacturer',Upload],...(user.role==='Admin'?[['audit','Audit Log',History] as [View,string,any]]:[])]},
  {label:'Tools',items:[['visual','Visual Search',ScanSearch],['verify','Verify Report',ShieldCheck]]},
 ];
 const navigate=(target:NavigationLocation)=>{
  const requestedLocation=normaliseNavigationLocation(target.view,target.reportId);
  const allowed=canAccessView(user.role,requestedLocation);
  const location=allowed?requestedLocation:{view:'dashboard' as View,reportId:null};
  const current=readNavigationLocation();
  const sameLocation=current.view===location.view&&current.reportId===location.reportId;
  const url=navigationUrl(location);
  if(!allowed)window.history.replaceState(navigationHistoryState(location,0),'',url);
  else if(!sameLocation){
   saveCurrentNavigationScroll();
   window.history.pushState(navigationHistoryState(location,0),'',url);
  }else if(url!==currentNavigationUrl())window.history.replaceState(navigationHistoryState(location,window.scrollY),'',url);
  setView(location.view);setOpenReportId(location.reportId);setMenu(false);setNavGroup(null);window.scrollTo({top:0,behavior:'smooth'});
 };
 const go=(v:View)=>navigate({view:v,reportId:null});
 const openExistingReport=(id:number)=>navigate({view:'evaluation',reportId:id});
 const logout=async()=>{await api('/api/auth/logout',{method:'POST'});setUser(null)};
 return <main><header className="topbar">
  <button className="brand" onClick={()=>go('dashboard')}><span className="brand-mark"><Scale size={24}/></span><span>NAWI<br/>LAB.</span></button>
  <nav className={menu?'nav open':'nav'}>
   <button className={`nav-direct${view==='dashboard'?' active':''}`} onClick={()=>go('dashboard')}><LayoutDashboard size={15}/>Overview</button>
   {navGroups.map(group=>{
    const items=group.items.filter(([id])=>canAccessView(user.role,{view:id,reportId:null}));
    if(!items.length)return null;
    const groupActive=items.some(([id])=>id===view);
    const groupOpen=navGroup===group.label;
    return <div
      className={`nav-group${groupActive?' active':''}${groupOpen?' open':''}`}
      key={group.label}
      onPointerEnter={e=>{if(e.pointerType==='mouse')setNavGroup(group.label)}}
      onPointerLeave={e=>{if(e.pointerType==='mouse')setNavGroup(current=>current===group.label?null:current)}}
    >
     <button
      type="button"
      className="nav-group-trigger"
      aria-expanded={groupOpen}
      aria-haspopup="menu"
      onClick={()=>setNavGroup(current=>current===group.label?null:group.label)}
     >
      {group.label}<ChevronDown className="nav-chevron" size={15}/>
     </button>
     <div className="nav-dropdown" role="menu">
      {items.map(([id,label,I])=><button key={id} role="menuitem" className={view===id?'active':''} onClick={()=>go(id)}><I size={15}/>{label}</button>)}
     </div>
    </div>
   })}
   <div className="nav-account"><span className="avatar">{user.username[0].toUpperCase()}</span><b>{user.username}</b><button type="button" className="logout-top" onClick={logout} aria-label="Log out"><LogOut size={15}/></button></div>
  </nav>
  <div className="user"><span className="avatar">{user.username[0].toUpperCase()}</span><b title={user.role}>{user.username}</b><button type="button" className="logout-top" onClick={logout} aria-label="Log out"><LogOut size={15}/></button></div>
  <button className="menu" onClick={()=>{setMenu(!menu);setNavGroup(null)}} aria-label="Toggle navigation"><Menu/></button>
 </header>
 {view==='dashboard'&&<Dashboard go={go} openExistingReport={openExistingReport} canCreateInstrument={canCreateInstrument} canCreateEvaluation={canCreateEvaluation} canAccessReports={canAccessReports}/>} {view==='instruments'&&<Instruments go={go} canCreateInstrument={canCreateInstrument} canUseLiveTest={canUseLiveTest}/>} {view==='evaluation'&&<Evaluation key={openReportId??'new'} go={go} user={user} openReportId={openReportId} onForbiddenReport={replaceForbiddenReportWithOverview} openExistingReport={openExistingReport}/>} {view==='reports'&&<Reports openExistingReport={openExistingReport}/>} {view==='live'&&<LiveTest/>} {view==='manufacturer'&&<Manufacturer/>} {view==='visual'&&<VisualSearch/>} {view==='verify'&&<Verify/>} {view==='audit'&&<Audit/>}
 <footer><div className="footer-brand">MEASURE.<br/><span>PROVE.</span><br/>REPORT.</div><div><b>NAWI LAB</b><p>OIML R76 implemented-core evaluation workspace<br/>Verification workflow</p></div><div><b>SYSTEM</b><p>Evidence capture · stored snapshots<br/>Implemented-core verification workflow</p></div></footer>
 {notice&&<Modal title={notice.title} close={()=>setNotice(null)}><p>{notice.body}</p><button className="primary" onClick={()=>setNotice(null)}>Got it <ArrowRight/></button></Modal>}
 </main>
}

function Login({onLogin,demoMode}:{onLogin:(u:User)=>void;demoMode:boolean}){const [u,setU]=useState(()=>demoMode?'admin':''),[p,setP]=useState(()=>demoMode?'admin123':''),[err,setErr]=useState('');const submit=async(e:any)=>{e.preventDefault();try{setErr('');const x=await post('/api/auth/login',{username:u,password:p});onLogin(x.user)}catch(x:any){setErr(x.message)}};return <div className="login-page"><div className="login-glow"/><div className="login-card"><div className="login-brand"><span className="brand-mark"><Scale/></span><div><b>NAWI<span> LAB.</span></b><small>Digital Passport Platform</small></div></div><div className="login-copy"><span className="eyebrow">LABORATORY • MANUFACTURER • REVIEW</span><h1>Verify every weighing instrument with confidence.</h1><p>Register an instrument, run the implemented-core tests, then submit for reviewer approval.</p></div><form onSubmit={submit}><label>Username<input value={u} onChange={e=>setU(e.target.value)}/></label><label>Password<input type="password" value={p} onChange={e=>setP(e.target.value)}/></label>{err&&<p className="error">{err}</p>}<button className="primary full">Sign in <ChevronRight/></button></form>{demoMode&&<div className="demo-creds"><b>Demo accounts</b><span>admin / admin123</span><span>tester / tester123</span><span>reviewer / reviewer123</span><span>manufacturer / manufacturer123</span></div>}</div></div>}

function Dashboard({go,openExistingReport,canCreateInstrument,canCreateEvaluation,canAccessReports}:{go:(v:View)=>void;openExistingReport:(id:number)=>void;canCreateInstrument:boolean;canCreateEvaluation:boolean;canAccessReports:boolean}){const [data,setData]=useState<any>(null);useEffect(()=>{api('/api/dashboard').then(setData)},[]);const restoreScrollY=typeof window==='undefined'?0:navigationScrollY(window.history.state);if(!data)return <div className="page" style={{minHeight:`calc(100vh + ${restoreScrollY}px)`}}><Empty text="Loading dashboard…"/></div>;const s=data.stats;return <><section className="hero"><div><span className="eyebrow">OIML R 76 · IMPLEMENTED-CORE EVALUATION</span><h1>Good data.<br/><em>No guesswork.</em></h1><p>Implemented-core OIML R76 verification—from registration to reviewer-approved report.</p>{(canCreateInstrument||canCreateEvaluation)&&<div className="actions">{canCreateInstrument&&<button className="primary" onClick={()=>go('instruments')}><Plus/> Register instrument</button>}{canCreateEvaluation&&<button className="text-btn" onClick={()=>go('evaluation')}>Start evaluation <ArrowRight/></button>}</div>}</div><div className="hero-art"><div className="dial"><Scale size={70}/><b>{s.instruments}</b><span>REGISTERED<br/>INSTRUMENTS</span></div><span className="orbit o1">Evidence first</span><span className="orbit o2">OIML R 76</span><span className="orbit o3">Digital passport</span></div></section><section className="metrics"><article className="metric blue"><Gauge/><strong>{s.instruments}</strong><span>Registered<br/>instruments</span></article><article className="metric red"><Activity/><strong>{s.in_progress}</strong><span>In progress<br/>reports</span></article><article className="metric yellow"><ClipboardCheck/><strong>{s.review}</strong><span>Pending<br/>review</span></article><article className="metric green"><FileCheck2/><strong>{s.passed}</strong><span>Technical PASS<br/>core scope</span></article></section>{canAccessReports&&<section className="work"><div className="section-head"><div><span className="eyebrow">RECENT VERIFICATION ACTIVITY</span><h2>Records that<br/>need attention.</h2></div><button className="outline" onClick={()=>go('reports')}>View reports <ArrowRight/></button></div><div className="eval-list">{data.recent.map((r:any,i:number)=><button className="eval-row" key={r.id} onClick={()=>openExistingReport(r.id)}><span className="eval-num">0{i+1}</span><div><b>{r.report_number}</b><h3>{r.instrument.model}</h3><small>{r.instrument.manufacturer} · {r.instrument.serial_number}</small></div><Result text={r.final_result}/><ChevronRight/></button>)}</div>{!data.recent.length&&<Empty text="No reports yet."/>}</section>}<section className="rules"><div className="rule-title"><FlaskConical/><h2>Verified rules.<br/>Visible workings.</h2></div><div><p>Every result keeps original observations separate from calculated values, preserves evidence, and records the configured rule version.</p><div className="rule-grid"><span><b>01</b>Missing data is never a pass.</span><span><b>02</b>Evidence stays linked to the report.</span><span><b>03</b>Approved reports remain traceable.</span></div></div></section></>}

function Instruments({go,canCreateInstrument,canUseLiveTest}:{go:(v:View)=>void;canCreateInstrument:boolean;canUseLiveTest:boolean}){const [items,setItems]=useState<Instrument[]>([]),[show,setShow]=useState(false);const load=()=>api('/api/instruments').then(setItems);useEffect(()=>{load()},[]);return <section className="page"><div className="page-title"><div><span className="eyebrow">INSTRUMENT REGISTER</span><h1>Know what<br/>you’re testing.</h1></div>{canCreateInstrument&&<button className="primary" onClick={()=>setShow(true)}><Plus/> New instrument</button>}</div>{show&&<InstrumentForm close={()=>setShow(false)} refresh={load}/>}<div className="instrument-cards">{items.map(i=><div className="instrument-card" key={i.id}><div className="instrument-visual"><Scale/><span>CLASS {i.accuracy_class}</span></div><div><Pill tone="green">Digital passport active</Pill><h2>{i.model}</h2><p>{i.manufacturer}</p><dl><div><dt>Serial number</dt><dd>{i.serial_number}</dd></div><div><dt>Max / Min</dt><dd>{i.max_capacity} / {i.min_capacity} {i.unit}</dd></div><div><dt>Verification / actual interval</dt><dd>e = {i.e} / d = {i.d}</dd></div><div><dt>Software</dt><dd>{i.software_version||'—'}</dd></div></dl>{canUseLiveTest&&<button className="primary" onClick={()=>go('live')}>Open live test <ArrowRight/></button>}</div></div>)}</div>{!items.length&&<Empty text="No instruments registered yet."/>}</section>}
function InstrumentForm({close,refresh}:{close:()=>void;refresh:()=>void}){
 const numericKeys=new Set(['min_capacity','max_capacity','e','d']);
 const [d,setD]=useState<any>({manufacturer:'',model:'',serial_number:'',accuracy_class:'III',min_capacity:'0.2',max_capacity:'30',e:'0.01',d:'0.01',unit:'kg',software_version:''});
 const [err,setErr]=useState('');
 const [classFail,setClassFail]=useState<InstrumentClassification|null>(null);
 const touch=(patch:any)=>{setErr('');setClassFail(null);setD((prev:any)=>({...prev,...patch}))};
 const save=async(e:any)=>{
  e.preventDefault();
  setErr('');setClassFail(null);
  try{
    await post('/api/instruments',d);
    close();refresh();
  }catch(x:any){
    setErr(x.message);
    if(x instanceof ApiRequestError && x.status===422 && x.body.classification){
      setClassFail(x.body.classification);
    }
  }
 };
 const nRange=classFail?(classFail.minimum_n==null?'Not applicable':classFail.maximum_n==null?`≥ ${classFail.minimum_n}`:`${classFail.minimum_n} – ${classFail.maximum_n}`):'';
 const requiredMin=classFail?(classFail.minimum_capacity_required==null?'Not applicable':`${classFail.minimum_capacity_required} ${classFail.unit}`):'';
 const requiredMinRule=classFail?(classFail.minimum_capacity_multiplier==null?'Not applicable':`${classFail.minimum_capacity_multiplier} d`):'';
 return <Modal title="Register instrument" close={close}><form className="form-grid" onSubmit={save}>
  {['manufacturer','model','serial_number','min_capacity','max_capacity','e','d','software_version'].map(k=>
    <label key={k}>{k.replaceAll('_',' ')}<input required={k!=='software_version'} type={numericKeys.has(k)?'number':'text'} step={numericKeys.has(k)?'any':undefined} value={d[k]} onChange={e=>touch({[k]:e.target.value})}/></label>
  )}
  <label>Accuracy class<select value={d.accuracy_class} onChange={e=>touch({accuracy_class:e.target.value})}><option>I</option><option>II</option><option>III</option><option>IIII</option></select></label>
  <label>Unit<select value={d.unit} onChange={e=>touch({unit:e.target.value})}><option>kg</option><option>g</option><option>t</option></select></label>
  {err&&<p className="error fullrow">{err}</p>}
  {classFail&&<div className="class-fail fullrow">
    <span className="eyebrow">OIML R76 CLASSIFICATION</span>
    <b>Declared Class {classFail.accuracy_class} does not satisfy Table 3</b>
    <dl className="calc-grid">
      <div><dt>n = Max/e</dt><dd>{classFail.number_of_verification_intervals}</dd></div>
      <div><dt>Allowed n</dt><dd>{nRange}</dd></div>
      <div><dt>Required Min</dt><dd>{classFail.minimum_capacity_required} {classFail.unit}</dd></div>
      <div><dt>Required Min rule</dt><dd>{classFail.minimum_capacity_multiplier} d</dd></div>
      <div><dt>Ruleset</dt><dd>{classFail.ruleset_version}</dd></div>
      <div><dt>Rule reference</dt><dd>{classFail.rule_reference}</dd></div>
    </dl>
    <ul>{classFail.errors.map((msg,i)=><li key={i}>{msg}</li>)}</ul>
  </div>}
  <div className="form-actions fullrow"><button type="button" className="outline" onClick={close}>Cancel</button><button className="primary">Create passport</button></div>
 </form></Modal>
}
function Evaluation({go,user,openReportId,onForbiddenReport,openExistingReport}:{go:(v:View)=>void;user:User;openReportId:number|null;onForbiddenReport:()=>void;openExistingReport:(id:number)=>void}){
 const [inst,setInst]=useState<Instrument[]>([]),[selected,setSelected]=useState(''),[report,setReport]=useState<Report|null>(null),[temp,setTemp]=useState('20.4'),[humidity,setHumidity]=useState('48'),[load,setLoad]=useState('10'),[ref,setRef]=useState('10'),[ind,setInd]=useState('10.002'),[zeroError,setZeroError]=useState(''),[additionalLoad,setAdditionalLoad]=useState(''),[saved,setSaved]=useState(false),[obsErr,setObsErr]=useState('');
 const [testSectionScrollOffset,setTestSectionScrollOffset]=useState(0);
 useEffect(()=>{api('/api/instruments').then(setInst)},[]);
 useEffect(()=>{
  const header=document.querySelector<HTMLElement>('.topbar');
  if(!header)return;
  const update=()=>setTestSectionScrollOffset(header.getBoundingClientRect().height);
  update();
  window.addEventListener('resize',update);
  return()=>window.removeEventListener('resize',update);
 },[]);
 useEffect(()=>{
  const clearLoadedReport=()=>{
   setReport(null);setSelected('');setTemp('20.4');setHumidity('48');setLoad('10');setRef('10');setInd('10.002');setZeroError('');setAdditionalLoad('');setSaved(false);setObsErr('');setWfErr('');
  };
  if(!openReportId){clearLoadedReport();return}
  let cancel=false;
  clearLoadedReport();
  api(`/api/reports/${openReportId}`).then(r=>{
   if(cancel)return;
   setReport(r);setSelected(String(r.instrument.id));if(r.temperature!=null)setTemp(String(r.temperature));if(r.humidity!=null)setHumidity(String(r.humidity));
  }).catch((x:any)=>{
   if(cancel)return;
   clearLoadedReport();
   if(x instanceof ApiRequestError&&x.status===403)onForbiddenReport();
  });
  return()=>{cancel=true};
 },[openReportId,onForbiddenReport]);
 const canEditTechnical=user.role==='Admin'||user.role==='Tester';
 const create=async()=>{
  if(!canEditTechnical||!selected)return;
  const created=await post('/api/reports',{
    instrument_id:Number(selected),
    laboratory:'NAWI Lab',
    location:'Laboratory Floor'
  });
  openExistingReport(created.id);
};
 const saveObs=async()=>{
  if(!report||!isReportEditable){setObsErr('Test data is locked');return};
  const roundingRequired=roundingRequiredFor(report.instrument);
  const applied=finiteNumber(load), L=finiteNumber(ref), I=finiteNumber(ind), E0=finiteNumber(zeroError);
  if(applied===null||applied<0){setObsErr('Applied load must be a number ≥ 0');return}
  if(L===null||L<0){setObsErr('Reference / canonical load L must be a number ≥ 0');return}
  if(I===null){setObsErr('Original indication I is required');return}
  if(zeroError===''||E0===null){setObsErr('Zero error E0 must be entered explicitly');return}
  let dL:number|null=null;
  if(roundingRequired){
    dL=finiteNumber(additionalLoad);
    if(additionalLoad===''||dL===null||dL<0){setObsErr('Additional load ΔL must be entered and ≥ 0');return}
  }
  const payload:any={test_type:'Accuracy Test',position:'Center',applied_load:applied,reference_value:L,indication:I,zero_error:E0,verification_stage:'initial'};
  if(roundingRequired) payload.additional_load=dL;
  try{
    setObsErr('');
    const r=await post(`/api/reports/${report.id}/observations`,payload);
    setReport(r);setSaved(true);setAdditionalLoad('');setTimeout(()=>setSaved(false),1800);
  }catch(x:any){setObsErr(x.message);setSaved(false)}
 };
 const saveEnv=async()=>{if(!report||!isReportEditable){setWfErr('Test data is locked');return}setReport(await post(`/api/reports/${report.id}/environment`,{temperature:temp,humidity:humidity,pressure:'1013',laboratory:'NAWI Lab',location:'Laboratory Floor'}))};
 const [wfErr,setWfErr]=useState('');
 const complete=async()=>{if(!report)return;setReport(await post(`/api/reports/${report.id}/complete`,{}))};
 const reloadReport=async()=>{if(!report)return;setReport(await api(`/api/reports/${report.id}`))};
 const weighingRef=useRef<HTMLDivElement>(null);
 const zeroSettingRef=useRef<HTMLDivElement>(null);
 const repeatabilityRef=useRef<HTMLDivElement>(null);
 const eccentricityRef=useRef<HTMLDivElement>(null);
 const tareWeighingRef=useRef<HTMLDivElement>(null);
 const scrollToSection=(ref:{current:HTMLDivElement|null})=>{ref.current?.scrollIntoView({behavior:'smooth',block:'start'})};
 const testSectionTargetStyle={scrollMarginTop:`${testSectionScrollOffset}px`};

 const unit=report?.instrument.unit||'';
 const isReportEditable=canEditTechnical&&(!report||report.status==='In Progress');
 const roundingRequired=report?roundingRequiredFor(report.instrument):false;
 const last=report?.observations.at(-1);
 return <section className="page eval-page"><div className="eval-header"><div><span className="eyebrow">IMPLEMENTED-CORE EVALUATION · OIML R 76</span><h1>Weighing<br/>performance.</h1><p>{report?`${report.report_number} · ${report.instrument.model}`:'Create a test session from a registered instrument.'}</p></div><div className="completion"><strong>{programmeProgress(report?.test_programme)}%</strong><span>progress</span></div></div>{!report?<div className="start-panel"><h2>Start evaluation</h2><select value={selected} onChange={e=>setSelected(e.target.value)}><option value="">Choose registered instrument</option>{inst.map(i=><option key={i.id} value={i.id}>{i.manufacturer} {i.model} — {i.serial_number}</option>)}</select>{canEditTechnical&&<button className="primary" disabled={!selected} onClick={create}>Create report <ArrowRight/></button>}</div>:<div className="workspace"><aside><span className="eyebrow">TEST PROGRAMME</span>
 <button type="button" className="nav-item" onClick={()=>scrollToSection(zeroSettingRef)}><span>1</span><div><b>Zero-setting accuracy</b><small>{!report.zero_setting?'Available':report.zero_setting.status==='PASS'?'Pass':report.zero_setting.status==='FAIL'?'Fail':report.zero_setting.status}</small></div></button>
 <button type="button" className="selected nav-item" onClick={()=>scrollToSection(weighingRef)}><span>2</span><div><b>Weighing performance</b><small>In progress</small></div></button>
 <button type="button" className="nav-item" onClick={()=>scrollToSection(eccentricityRef)}><span>3</span><div><b>Eccentric loading</b><small>Available</small></div></button>
 <button type="button" className="nav-item" onClick={()=>scrollToSection(repeatabilityRef)}><span>4</span><div><b>Repeatability</b><small>Available</small></div></button>
 <button type="button" className="nav-item" onClick={()=>scrollToSection(tareWeighingRef)}><span>5</span><div><b>Tare weighing</b><small>{!report.tare_weighing?'Available':report.tare_weighing.status==='PASS'?'Pass':report.tare_weighing.status==='FAIL'?'Fail':report.tare_weighing.status==='INCOMPLETE'?'Incomplete':report.tare_weighing.status}</small></div></button>
 </aside><div className="test-form"><div><div className="form-head"><div><Badge text={report.status}/><h2>Increasing load observations</h2><p>Original indications are stored with the verified OIML calculation.</p></div><span className="rule-version">RULE SET<br/><b>{report.standard_name} · {report.standard_version}</b></span></div></div><h3>Laboratory conditions</h3><div className="fields"><label>Temperature<span><input type="number" value={temp} onChange={e=>setTemp(e.target.value)} disabled={!isReportEditable}/><i>°C</i></span></label><label>Humidity<span><input type="number" value={humidity} onChange={e=>setHumidity(e.target.value)} disabled={!isReportEditable}/><i>% RH</i></span></label><label>Pressure<span><input type="number" value="1013" readOnly/><i>hPa</i></span></label></div><button className="outline env-save" onClick={saveEnv} disabled={!isReportEditable}>Save conditions</button>{report.test_programme&&<ProgrammePanel prog={report.test_programme}/>}{<WorkflowPanel report={report} user={user} onReload={reloadReport} onError={setWfErr}/>}{wfErr&&<p className="error">{wfErr}</p>}<div ref={zeroSettingRef} id="zero-setting-accuracy" style={testSectionTargetStyle}><ZeroSettingCard reportId={report.id} unit={unit} snapshot={report.zero_setting||null} roundingRequired={roundingRequired} reload={reloadReport} disabled={!isReportEditable}/></div><div ref={repeatabilityRef} id="repeatability" className="module-grid" style={testSectionTargetStyle}><RepeatabilityCard reportId={report.id} title="Repeatability — Half Max" role="half_max" unit={unit} snapshot={report.repeatability?.half_max||null} reload={reloadReport} disabled={!isReportEditable}/><RepeatabilityCard reportId={report.id} title="Repeatability — Near Max" role="near_max" unit={unit} snapshot={report.repeatability?.near_max||null} reload={reloadReport} disabled={!isReportEditable}/></div><div ref={eccentricityRef} id="eccentricity" style={testSectionTargetStyle}><EccentricityCard reportId={report.id} unit={unit} snapshot={report.eccentricity||null} reload={reloadReport} disabled={!isReportEditable}/></div><div ref={tareWeighingRef} id="tare-weighing" style={testSectionTargetStyle}><TareWeighingCard reportId={report.id} unit={unit} snapshot={report.tare_weighing||null} roundingRequired={roundingRequired} reload={reloadReport} disabled={!isReportEditable}/></div><div ref={weighingRef} id="weighing-performance" style={testSectionTargetStyle}><h3>Observation</h3><div className="fields obs-fields"><label>Applied load<span><input type="number" step="any" value={load} onChange={e=>setLoad(e.target.value)} disabled={!isReportEditable}/><i>{unit}</i></span></label><label>Reference / canonical load L<span><input type="number" step="any" value={ref} onChange={e=>setRef(e.target.value)} disabled={!isReportEditable}/><i>{unit}</i></span></label><label>Original indication I<span><input type="number" step="any" value={ind} onChange={e=>setInd(e.target.value)} disabled={!isReportEditable}/><i>{unit}</i></span></label><label>Zero error E0<span><input type="number" step="any" value={zeroError} onChange={e=>setZeroError(e.target.value)} placeholder="Required" disabled={!isReportEditable}/><i>{unit}</i></span></label>{roundingRequired&&<label>Additional load ΔL<span><input type="number" step="any" value={additionalLoad} onChange={e=>setAdditionalLoad(e.target.value)} placeholder="Required" disabled={!isReportEditable}/><i>{unit}</i></span></label>}</div>{roundingRequired?<p className="method-note">Rounding elimination is required because d &gt; 0.2e. Enter the additional load used to reach the next indication changeover point.</p>:<p className="method-note">Direct indication method — d ≤ 0.2e.</p>}<div className="observation-table"><div className="tr th"><span>Applied load</span><span>Indication</span><span>Corrected error</span><span>Outcome</span></div><div className="tr"><span>{last?`${last.applied_load} ${unit}`:`${load} ${unit}`}</span><span>{last?`${last.indication} ${unit}`:`${ind} ${unit}`}</span><span className="calc">{last?(last.calculation?`${last.calculation.corrected_error} ${unit}`:'—'):'Calculated on save'}</span><Result text={last?.result||'PENDING'}/></div></div>{obsErr&&<p className="error">{obsErr}</p>}<button className="primary" onClick={saveObs} disabled={!isReportEditable}>{saved&&<Check/>} Save reading</button>{last&&<CalculationPanel obs={last} unit={unit}/>}<div className="form-actions"><button className="outline" onClick={()=>window.open(`/api/reports/${report.id}/pdf`,'_blank')}><Printer/> Download PDF Report</button><button className="outline" onClick={()=>window.open(`/api/reports/${report.id}/word`,'_blank')}>Download DOCX Report</button></div></div></div></div>}</section>
}
function Reports({openExistingReport}:{openExistingReport:(id:number)=>void}){const [rows,setRows]=useState<Report[]>([]),[q,setQ]=useState('');const load=()=>api('/api/reports?q='+encodeURIComponent(q)).then(setRows);useEffect(()=>{load()},[q]);return <section className="page reports-page"><div className="page-title"><div><span className="eyebrow">CONTROLLED RECORDS</span><h1>Find it.<br/>Prove it.</h1></div><Archive size={100}/></div><div className="searchbar"><Search/><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search report no., maker, model or serial…"/></div><div className="report-table"><div className="report-row report-head"><span>Report</span><span>Instrument</span><span>Date</span><span>Status</span><span>Actions</span></div>{rows.map(r=><div className="report-row" key={r.id}><div><b>{r.report_number}</b><small>{r.standard_name} · {r.standard_version}</small></div><div><b>{r.instrument.model}</b><small>{r.instrument.manufacturer} · {r.instrument.serial_number}</small></div><div>{new Date(r.created_at).toLocaleDateString()}</div><div><Badge text={r.status}/><small>{r.final_result}</small></div><div className="row-actions"><button type="button" onClick={()=>openExistingReport(r.id)}>Open report</button><button onClick={()=>window.open(`/api/reports/${r.id}/pdf`,'_blank')}><Download/></button><button onClick={()=>window.open(`/api/reports/${r.id}/word`,'_blank')}>DOCX</button></div></div>)}</div>{!rows.length&&<Empty text="No reports match your search."/>}<p className="fineprint">Reports are generated from stored instrument, observation, environment and evidence data.</p></section>}

function LiveTest(){const [inst,setInst]=useState<Instrument[]>([]),[selected,setSelected]=useState(''),[report,setReport]=useState<Report|null>(null),[recording,setRecording]=useState(false),[videoUrl,setVideoUrl]=useState(''),[start,setStart]=useState<Date|null>(null);const videoRef=useRef<HTMLVideoElement>(null),recRef=useRef<MediaRecorder|null>(null),chunks=useRef<Blob[]>([]);useEffect(()=>{api('/api/instruments').then(setInst)},[]);const create=async()=>setReport(await post('/api/reports',{instrument_id:Number(selected),laboratory:'NAWI Lab',location:'Laboratory Floor'}));const startRec=async()=>{if(!report)return;const s=await navigator.mediaDevices.getUserMedia({video:true,audio:true});videoRef.current!.srcObject=s;chunks.current=[];const mime=MediaRecorder.isTypeSupported('video/webm;codecs=vp9')?'video/webm;codecs=vp9':'video/webm';const rec=new MediaRecorder(s,{mimeType:mime});rec.ondataavailable=e=>e.data.size&&chunks.current.push(e.data);rec.onstop=()=>{const blob=new Blob(chunks.current,{type:'video/webm'});setVideoUrl(URL.createObjectURL(blob));s.getTracks().forEach(t=>t.stop())};rec.start(500);recRef.current=rec;setStart(new Date());setRecording(true)};const stopRec=async()=>{if(!report)return;const end=new Date();recRef.current?.stop();setRecording(false);setTimeout(async()=>{const blob=new Blob(chunks.current,{type:'video/webm'});const fd=new FormData();fd.append('video',blob,'live-test.webm');fd.append('started_at',start?.toISOString()||'');fd.append('ended_at',end.toISOString());setReport(await api(`/api/reports/${report.id}/evidence`,{method:'POST',body:fd}))},800)};return <section className="page"><div className="page-title"><div><span className="eyebrow">EVIDENCE CAPTURE</span><h1>Prove the<br/>test.</h1></div><Video size={100}/></div><div className="live-layout"><div className="video-panel"><div className="camera"><video ref={videoRef} autoPlay muted playsInline/><div className="camera-overlay"><span>NAWI LAB</span>{report&&<span>{report.report_number}</span>}<strong>{recording?'TEST IN PROGRESS':'READY'}</strong></div></div><div className="camera-actions">{!report?<button className="primary" disabled={!selected} onClick={create}><Play/> Create test session</button>:!recording?<button className="primary" onClick={startRec}><Camera/> Start recording</button>:<button className="primary danger" onClick={stopRec}><Square/> Stop & secure evidence</button>}{videoUrl&&<span className="secured"><ShieldCheck/> Video captured and hash stored</span>}</div></div><div className="side-panel"><span className="eyebrow">TEST SESSION</span><h3>Select instrument</h3><select value={selected} disabled={!!report} onChange={e=>setSelected(e.target.value)}><option value="">Choose a registered scale</option>{inst.map(i=><option key={i.id} value={i.id}>{i.manufacturer} {i.model} — {i.serial_number}</option>)}</select>{report?<div className="session-panel"><Badge text={report.status}/><p>{report.report_number}</p><ObservationMini report={report} setReport={setReport}/></div>:<div className="warning"><Activity/><div><b>Evidence-first testing</b><p>The browser records the tester camera session. The server stores the video and SHA-256 hash against the report.</p></div></div>}</div></div></section>}
function ObservationMini({report,setReport}:{report:Report;setReport:(r:Report)=>void}){
 const unit=report.instrument.unit;
 const roundingRequired=roundingRequiredFor(report.instrument);
 const [d,setD]=useState({test_type:'Accuracy Test',position:'Center',applied_load:'10',reference_value:'10',indication:'10.002',zero_error:'',additional_load:'',notes:''});
 const [err,setErr]=useState('');
 const save=async(e:any)=>{
  e.preventDefault();
  const applied=finiteNumber(d.applied_load), L=finiteNumber(d.reference_value), I=finiteNumber(d.indication), E0=finiteNumber(d.zero_error);
  if(applied===null||applied<0){setErr('Applied load must be a number ≥ 0');return}
  if(L===null||L<0){setErr('Reference / canonical load L must be a number ≥ 0');return}
  if(I===null){setErr('Original indication I is required');return}
  if(d.zero_error===''||E0===null){setErr('Zero error E0 must be entered explicitly');return}
  let dL:number|null=null;
  if(roundingRequired){
    dL=finiteNumber(d.additional_load);
    if(d.additional_load===''||dL===null||dL<0){setErr('Additional load ΔL must be entered and ≥ 0');return}
  }
  const payload:any={test_type:d.test_type,position:d.position,applied_load:applied,reference_value:L,indication:I,zero_error:E0,verification_stage:'initial',notes:d.notes};
  if(roundingRequired) payload.additional_load=dL;
  try{setErr('');setReport(await post(`/api/reports/${report.id}/observations`,payload));setD({...d,additional_load:''})}catch(x:any){setErr(x.message)}
 };
 const last=report.observations.at(-1);
 return <form onSubmit={save} className="mini-form">
  <label>Test type<select value={d.test_type} onChange={e=>setD({...d,test_type:e.target.value})}><option>Accuracy Test</option><option>Repeatability</option><option>Eccentricity</option><option>Zero Return</option></select></label>
  <label>Applied load ({unit})<input type="number" step="any" value={d.applied_load} onChange={e=>setD({...d,applied_load:e.target.value})}/></label>
  <label>Reference / L ({unit})<input type="number" step="any" value={d.reference_value} onChange={e=>setD({...d,reference_value:e.target.value})}/></label>
  <label>Indication I ({unit})<input type="number" step="any" value={d.indication} onChange={e=>setD({...d,indication:e.target.value})}/></label>
  <label>Zero error E0 ({unit})<input type="number" step="any" value={d.zero_error} onChange={e=>setD({...d,zero_error:e.target.value})} placeholder="Required"/></label>
  {roundingRequired&&<label>Additional load ΔL ({unit})<input type="number" step="any" value={d.additional_load} onChange={e=>setD({...d,additional_load:e.target.value})} placeholder="Required"/></label>}
  {roundingRequired?<p className="method-note">Rounding elimination is required because d &gt; 0.2e.</p>:<p className="method-note">Direct indication method — d ≤ 0.2e.</p>}
  {err&&<p className="error">{err}</p>}
  <button className="secondary full">Save reading</button>
  {last&&<CalculationPanel obs={last} unit={unit}/>}
 </form>
}
function Manufacturer(){const [items,setItems]=useState<Instrument[]>([]),[selected,setSelected]=useState<Instrument|null>(null),[files,setFiles]=useState<FileList|null>(null);const load=()=>api('/api/instruments').then(setItems);useEffect(()=>{load()},[]);const upload=async()=>{if(!selected||!files?.length)return;const fd=new FormData();Array.from(files).forEach(f=>fd.append('images',f));await api(`/api/instruments/${selected.id}/images`,{method:'POST',body:fd});setSelected(null);setFiles(null);load()};return <section className="page"><div className="page-title"><div><span className="eyebrow">MANUFACTURER STUDIO</span><h1>Show the<br/>instrument.</h1></div><Upload size={100}/></div><div className="cards-grid">{items.map(i=><div className="product-card" key={i.id}><div className="product-image">{i.images[0]?<img src={i.images[0]}/>:<Scale size={60}/>}</div><span className="eyebrow">{i.manufacturer}</span><h3>{i.model}</h3><p>{i.serial_number}</p><button className="outline full" onClick={()=>setSelected(i)}><Upload/> Add product photos</button></div>)}</div>{selected&&<Modal title={`Photos · ${selected.model}`} close={()=>setSelected(null)}><div className="dropzone"><Upload size={32}/><b>Upload clear product photos</b><p>Front, side and label/serial views work best.</p><input type="file" accept="image/*" multiple onChange={e=>setFiles(e.target.files)}/></div><div className="form-actions"><button className="outline" onClick={()=>setSelected(null)}>Cancel</button><button className="primary" onClick={upload}>Save photos</button></div></Modal>}</section>}

function VisualSearch(){const [file,setFile]=useState<File|null>(null),[results,setResults]=useState<any[]>([]),[busy,setBusy]=useState(false);const search=async()=>{if(!file)return;setBusy(true);const fd=new FormData();fd.append('image',file);try{setResults((await api('/api/visual-search',{method:'POST',body:fd})).results)}finally{setBusy(false)}};return <section className="page"><div className="search-hero"><div><span className="eyebrow">AI-ASSISTED IDENTIFICATION</span><h1>Point. Upload.<br/><em>Identify.</em></h1><p>Upload a photo and find the closest registered product images.</p></div><div className="scan-orb"><ScanSearch size={58}/></div></div><div className="visual-grid"><div className="upload-card"><div className="dropzone big"><Camera size={34}/><h3>Upload a scale photo</h3><p>JPG, PNG or WEBP</p><input type="file" accept="image/*" onChange={e=>setFile(e.target.files?.[0]||null)}/>{file&&<div>✓ {file.name}</div>}<button className="primary" disabled={!file||busy} onClick={search}>{busy?'Matching…':'Find matching instruments'}</button></div></div><div className="results"><div className="section-head"><div><h3>Possible matches</h3><p>Highest visual similarity first</p></div></div>{results.map(r=><div className="match" key={r.instrument.id}><div className="match-image">{r.instrument.images[0]?<img src={r.instrument.images[0]}/>:<Scale/>}</div><div><span className="eyebrow">{r.instrument.manufacturer}</span><h3>{r.instrument.model}</h3><p>{r.instrument.serial_number}</p><div className="progress"><i style={{width:`${r.confidence}%`}}/></div></div><strong>{r.confidence}%</strong></div>)}{!results.length&&<Empty text="Upload an image to see matching instruments."/>}</div></div></section>}

function Verify(){const [id,setId]=useState(''),[data,setData]=useState<any>(null),[err,setErr]=useState('');const check=async(e:any)=>{e.preventDefault();try{setErr('');setData(await api('/api/verify/'+encodeURIComponent(id)))}catch(x:any){setErr(x.message);setData(null)}};return <section className="page verify-page"><div className="verify-card"><div className="verify-icon"><ShieldCheck/></div><span className="eyebrow">PUBLIC AUTHENTICITY CHECK</span><h1>Verify a test report</h1><p>Enter the report number printed on the report or linked from its QR code.</p><form onSubmit={check} className="verify-form"><input value={id} onChange={e=>setId(e.target.value)} placeholder="NAWI-20260902-123456-ABCD"/><button className="primary">Verify <ShieldCheck/></button></form>{err&&<p className="error">{err}</p>}{data&&<div className="verified"><div className="verified-top"><CheckCircle2/><div><b>Report authenticity record found</b><span>{data.report_number}</span></div></div><div className="verify-details"><div><small>Instrument</small><b>{data.instrument.manufacturer} {data.instrument.model}</b></div><div><small>Serial</small><b>{data.instrument.serial_number}</b></div><div><small>Result</small><Result text={data.final_result}/></div><div><small>Evidence</small><b>{data.evidence_count} file(s)</b></div></div><div className="integrity"><ShieldCheck/> Evidence integrity record available</div></div>}</div></section>}
function Audit(){const [items,setItems]=useState<any[]>([]);useEffect(()=>{api('/api/audit').then(setItems)},[]);return <section className="page"><div className="page-title"><div><span className="eyebrow">SYSTEM TRACE</span><h1>Audit<br/>everything.</h1></div><History size={100}/></div><div className="report-table"><div className="report-row report-head"><span>Time</span><span>User</span><span>Action</span><span>Report</span></div>{items.map(x=><div className="report-row audit-row" key={x.id}><span>{new Date(x.created_at).toLocaleString()}</span><span>{x.user}</span><span>{x.action}</span><span>{x.report_id||'—'}</span></div>)}</div></section>}
