import json,re,math
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path('.')
RAW=ROOT/'ml/data/raw/pvdaq/9068/source_objects'
OUT=ROOT/'ml/data/reports/pvdaq/9068/phase_c2_3'
META=ROOT/'ml/data/raw/pvdaq/9068/metadata/9068_system_metadata.json'
IRR_PATH=RAW/'9068_irradiance_data_20240101_20250430.csv'
ENV_PATH=RAW/'9068_environment_data_20240101_20250430.csv'
PAD1='pyranometer_(class_a)_pad_1_poa_irradiance_(w/m2)_o_149723'
PAD1_TC='pyranometer_(class_a)_pad_1_poa_irradiance_temp_compensated_(w/m2)_o_149724'
PAD2='pyranometer_(class_a)_pad_2_poa_irradiance_(w/m2)_o_149725'
PAD2_TC='pyranometer_(class_a)_pad_2_poa_irradiance_temp_compensated_(w/m2)_o_149726'
AMB='weather_station_ambient_temperature_(c)_o_149727'
MODULES=[f'thermocouple_pad_{pad}_back-of-module_temperature_{s}_(c)_o_{mid}' for pad,s,mid in [(1,1,149728),(1,2,149729),(2,1,149730),(2,2,149731)]]
POA=[PAD1,PAD1_TC,PAD2,PAD2_TC]

with META.open(encoding='utf-8') as f: metadata=json.load(f)
metric_records={int(v['metric_id']):v for v in metadata['Metrics'].values()}

def load_source(path):
    df=pd.read_csv(path,low_memory=False)
    df['_ts']=pd.to_datetime(df['measured_on'],errors='coerce')
    return df

irr=load_source(IRR_PATH)
env=load_source(ENV_PATH)


def col_id(c):
    m=re.search(r'_(\d+)$',c)
    return int(m.group(1)) if m else None

def metadata_row(c):
    mid=col_id(c); m=metric_records.get(mid,{})
    return {'metric_id':mid,'metadata_key':next((k for k,v in metadata['Metrics'].items() if v.get('metric_id')==mid),None),
      'documented_sensor_name':m.get('sensor_name'),'documented_common_name':m.get('common_name'),'description_field':'sensor_name (no separate description field)',
      'raw_units':m.get('raw_units'),'units':m.get('units'),'aggregation_type':m.get('aggregation_type'),'source_type':m.get('source_type'),
      'source_id':m.get('source_id'),'hardware_mapping':'unavailable (source_id is null)' if m.get('source_id') is None else str(m.get('source_id')),
      'calc_scale':m.get('calc_scale'),'calc_offset':m.get('calc_offset'),'calc_details':m.get('calc_details'),'comments':m.get('comments'),'offline':m.get('offline')}

def exact_runs(series,ts,min_count=12,nonzero_only=False):
    v=series.to_numpy(dtype=float); t=pd.DatetimeIndex(ts); n=len(v)
    if not n:return []
    # A run is broken by a missing value, a value change, or non-five-minute timestamp spacing.
    breaks=np.ones(n,dtype=bool); breaks[0]=True
    for i in range(1,n):
        breaks[i]=(not np.isfinite(v[i]) or not np.isfinite(v[i-1]) or v[i]!=v[i-1] or t[i]-t[i-1]!=pd.Timedelta(minutes=5))
    # Include transition after a value when next sample changes.
    starts=np.flatnonzero(breaks)
    rec=[]
    for k,s in enumerate(starts):
        e=starts[k+1] if k+1<len(starts) else n
        if not np.isfinite(v[s]): continue
        count=e-s
        if count>=min_count and (not nonzero_only or v[s]!=0):
            rec.append({'start':t[s].isoformat(),'end':t[e-1].isoformat(),'count':int(count),'elapsed_minutes_between_labels':float((t[e-1]-t[s]).total_seconds()/60),'value':float(v[s])})
    return rec

def source_time_info(df):
    ts=df['_ts'].dropna(); d=ts.diff().dropna()
    off=((ts.dt.minute%5)!=0)|(ts.dt.second!=0)|(ts.dt.microsecond!=0)
    grid=pd.date_range(ts.min(),ts.max(),freq='5min') if len(ts) else pd.DatetimeIndex([])
    return {'source_rows':int(len(df)),'timestamp_parse_failures':int(df['_ts'].isna().sum()),'unique_timestamps':int(ts.nunique()),
      'duplicate_timestamp_excess_rows':int(ts.duplicated().sum()),'source_order_monotonic':bool(ts.is_monotonic_increasing),
      'off_grid_timestamp_rows':int(off.sum()),'first_timestamp':ts.min().isoformat() if len(ts) else None,'last_timestamp':ts.max().isoformat() if len(ts) else None,
      'expected_5m_grid_labels_first_to_last':int(len(grid)),'missing_grid_labels':int(len(grid)-ts.nunique()),
      'adjacent_5m_deltas':int((d==pd.Timedelta(minutes=5)).sum()),'adjacent_non5m_deltas':int((d!=pd.Timedelta(minutes=5)).sum()),
      'adjacent_delta_distribution_minutes':{str(float(k.total_seconds()/60)):int(v) for k,v in d.value_counts().sort_index().items()}}

irr_time=source_time_info(irr); env_time=source_time_info(env)
# Source rows are unique in these objects; retain the original timestamp index and source order.
irr=irr.loc[irr['_ts'].notna()].set_index('_ts').sort_index()
env=env.loc[env['_ts'].notna()].set_index('_ts').sort_index()
start=max(irr.index.min(),env.index.min()); end=min(irr.index.max(),env.index.max())
grid=pd.date_range(min(irr.index.min(),env.index.min()),max(irr.index.max(),env.index.max()),freq='5min')
# Numeric copies for calculations; raw data remains untouched.
irr_non_numeric={}
env_non_numeric={}
for c in irr.columns:
    if c not in ['measured_on']: irr[c]=pd.to_numeric(irr[c],errors='coerce')
for c in env.columns:
    if c not in ['measured_on']: env[c]=pd.to_numeric(env[c],errors='coerce')

# Distinguish blank cells from nonblank values that fail numeric parsing.
# The loaded numeric frames above intentionally preserve blanks as NaN.
for path, target in [(IRR_PATH, irr_non_numeric), (ENV_PATH, env_non_numeric)]:
    raw=pd.read_csv(path,low_memory=False)
    for c in [x for x in raw.columns if x!='measured_on']:
        text=raw[c].astype('string').str.strip()
        parsed=pd.to_numeric(text,errors='coerce')
        target[c]=int((text.notna() & text.ne('') & parsed.isna()).sum())

# Channel-level complete inventory for all source columns, with official metric fields.
inventory=[]
for file_name,df,info in [('9068_irradiance_data_20240101_20250430.csv',irr,irr_time),('9068_environment_data_20240101_20250430.csv',env,env_time)]:
    for c in [x for x in df.columns if x!='measured_on']:
        x=df[c]; vals=x.dropna(); meta=metadata_row(c)
        q=vals.quantile([0,.01,.05,.25,.5,.75,.95,.99,1]) if len(vals) else pd.Series(dtype=float)
        inventory.append({'source_file':file_name,'column_name':c,**meta,'first_numeric_timestamp':vals.index.min().isoformat() if len(vals) else None,
          'last_numeric_timestamp':vals.index.max().isoformat() if len(vals) else None,'source_rows':info['source_rows'],'numeric_observations':int(x.notna().sum()),
          'missing_values_on_source_rows':int(x.isna().sum()),'missing_pct_on_source_rows':float(x.isna().mean()*100),
          'min':float(vals.min()) if len(vals) else None,'p01':float(q.loc[.01]) if len(vals) else None,'p05':float(q.loc[.05]) if len(vals) else None,
          'median':float(vals.median()) if len(vals) else None,'mean':float(vals.mean()) if len(vals) else None,'p95':float(q.loc[.95]) if len(vals) else None,'p99':float(q.loc[.99]) if len(vals) else None,'max':float(vals.max()) if len(vals) else None,
          'timestamp_parse_failures_source':info['timestamp_parse_failures'],'duplicate_timestamp_excess_rows_source':info['duplicate_timestamp_excess_rows'],
          'off_grid_timestamp_rows_source':info['off_grid_timestamp_rows'],'source_adjacent_non5m_deltas':info['adjacent_non5m_deltas'],
          'non_numeric_nonblank_count':(irr_non_numeric if file_name.startswith('9068_irradiance') else env_non_numeric).get(c,0),'zero_count':int((x==0).sum()),'negative_count':int((x<0).sum())})
inv=pd.DataFrame(inventory)
inv.to_csv(OUT/'environment_channel_inventory.csv',index=False)

# List documented meteorological/environment metrics absent from the authorized irradiance/environment objects.
seen_ids={col_id(c) for c in list(irr.columns)+list(env.columns) if c!='measured_on'}
absent=[]
for mid,m in metric_records.items():
    common=str(m.get('common_name','')).lower(); sensor=str(m.get('sensor_name','')).lower()
    if any(term in common or term in sensor for term in ['irradiance','wind','temperature ambient','temperature module']):
        if mid not in seen_ids:
            absent.append({'metric_id':mid,'metadata_key':next((k for k,v in metadata['Metrics'].items() if v.get('metric_id')==mid),None),
              'sensor_name':m.get('sensor_name'),'common_name':m.get('common_name'),'units':m.get('units'),'aggregation_type':m.get('aggregation_type'),
              'source_type':m.get('source_type'),'source_id':m.get('source_id'),'reason':'listed in System metadata but absent from the approved irradiance/environment source headers'})
pd.DataFrame(absent).to_csv(OUT/'metadata_environment_channels_absent.csv',index=False)

# Reindex selected channels to the exact expected 5-minute grid; missing remains NaN.
sel_irr=irr[POA].reindex(grid)
sel_env=env[[AMB,*MODULES]].reindex(grid)
# Daylight proxy: at least one of the two raw POA sensors is >50 W/m2. This is an operational classification only.
daylight=(sel_irr[PAD1].gt(50)|sel_irr[PAD2].gt(50)).fillna(False)

def summary(x):
    v=x.dropna(); q=v.quantile([.01,.05,.25,.5,.75,.95,.99]) if len(v) else pd.Series(dtype=float)
    return {'numeric_observations':int(x.notna().sum()),'missing_on_expected_grid':int(x.isna().sum()),'missing_pct_expected_grid':float(x.isna().mean()*100),
      'first_numeric_timestamp':v.index.min().isoformat() if len(v) else None,'last_numeric_timestamp':v.index.max().isoformat() if len(v) else None,
      'min':float(v.min()) if len(v) else None,'mean':float(v.mean()) if len(v) else None,'median':float(v.median()) if len(v) else None,'max':float(v.max()) if len(v) else None,
      'percentiles':{str(k):float(val) for k,val in q.items()},'negative_count':int((x<0).sum()),'zero_count':int((x==0).sum()),
      'negative_when_daylight_proxy':int(((x<0)&daylight).sum()),'daylight_proxy_numeric':int((x.notna()&daylight).sum()),
      'daylight_proxy_missing':int((x.isna()&daylight).sum())}

# Complete POA summaries and targeted abrupt-transition counts.
poa_summaries={}
for c in POA:
    x=sel_irr[c]; d=x.diff(); dt=grid.to_series().diff()
    consecutive=(dt==pd.Timedelta(minutes=5))
    poa_summaries[c]={**summary(x),'abs_step_gt_200_wm2':int((d.abs().gt(200)&consecutive).sum()),'abs_step_gt_500_wm2':int((d.abs().gt(500)&consecutive).sum()),
      'p99_abs_5m_step_wm2':float(d[consecutive].abs().quantile(.99)) if (consecutive&d.notna()).any() else None,
      'longest_constant_run':max(exact_runs(x,grid,min_count=2),key=lambda r:r['count'],default=None),
      'nonzero_constant_runs_ge_60min':[r for r in exact_runs(x,grid,min_count=12,nonzero_only=True) if r['count']>=12]}
# save nonzero flatline runs >= 60 min, including counterpart ranges
plateaus=[]
for c,other in [(PAD1,PAD2),(PAD1_TC,PAD2_TC),(PAD2,PAD1),(PAD2_TC,PAD1_TC)]:
    for r in exact_runs(sel_irr[c],grid,min_count=12,nonzero_only=True):
        a=pd.Timestamp(r['start']); b=pd.Timestamp(r['end']); opp=sel_irr.loc[a:b,other].dropna()
        plateaus.append({'channel':c,'comparison_channel':other,**r,'other_channel_min':float(opp.min()) if len(opp) else None,'other_channel_max':float(opp.max()) if len(opp) else None,
          'other_channel_range':float(opp.max()-opp.min()) if len(opp) else None,'other_channel_numeric_count':int(len(opp))})
pd.DataFrame(plateaus).to_csv(OUT/'poa_nonzero_plateau_runs_ge60min.csv',index=False)

# All POA channel daily/monthly numeric coverage within the available expected grid.
coverage=[]
for period,freq in [('daily','D'),('monthly','MS')]:
    if period=='daily': groups=pd.Series(grid,index=grid).groupby(grid.normalize())
    else: groups=pd.Series(grid,index=grid).groupby(grid.to_period('M'))
    for key,idxs in groups:
        idx=pd.DatetimeIndex(idxs.values)
        label=key.isoformat() if hasattr(key,'isoformat') else str(key)
        for c in POA:
            x=sel_irr.loc[idx,c]; expected=len(idx); numeric=int(x.notna().sum())
            coverage.append({'period':period,'period_start':label,'channel':c,'expected_five_minute_labels_in_available_grid':expected,'numeric_observations':numeric,'missing_labels_or_values':expected-numeric,'coverage_pct':100*numeric/expected if expected else None,'daily_or_monthly_mean':float(x.mean()) if numeric else None,'daily_or_monthly_max':float(x.max()) if numeric else None})
cov=pd.DataFrame(coverage)
cov[cov.period=='daily'].to_csv(OUT/'poa_daily_coverage.csv',index=False)
cov[cov.period=='monthly'].to_csv(OUT/'poa_monthly_coverage.csv',index=False)

# Paired sensor comparisons, raw channels are primary for this comparison; temperature-compensated variants analyzed for consistency.
raw=sel_irr[[PAD1,PAD2]].dropna(); a=raw[PAD1]; b=raw[PAD2]; diff=a-b; avg=(a+b)/2
ratio_ok=b>50; ratio=(a[ratio_ok]/b[ratio_ok])
def compare_subset(mask,name):
    z=raw.loc[mask]; aa=z[PAD1]; bb=z[PAD2]; dd=aa-bb; rr=aa/bb.where(bb>50)
    return {'band':name,'n':int(len(z)),'pearson':float(aa.corr(bb)) if len(z)>1 else None,'spearman':float(aa.corr(bb,method='spearman')) if len(z)>1 else None,
      'difference_pad1_minus_pad2':{'mean':float(dd.mean()) if len(z) else None,'median':float(dd.median()) if len(z) else None,'mae':float(dd.abs().mean()) if len(z) else None,
        'p05':float(dd.quantile(.05)) if len(z) else None,'p95':float(dd.quantile(.95)) if len(z) else None,'abs_gt_50':int((dd.abs()>50).sum()),'abs_gt_100':int((dd.abs()>100).sum()),'abs_gt_200':int((dd.abs()>200).sum())},
      'ratio_pad1_over_pad2_when_pad2_gt_50':{'n':int(rr.notna().sum()),'p05':float(rr.dropna().quantile(.05)) if rr.notna().any() else None,'median':float(rr.dropna().median()) if rr.notna().any() else None,'p95':float(rr.dropna().quantile(.95)) if rr.notna().any() else None}}
refband=pd.cut(avg,[-np.inf,50,800,np.inf],labels=['low <=50','medium >50 to 800','high >800'])
paired={'n_common_raw_pairs':int(len(raw)),'pearson_all':float(a.corr(b)),'spearman_all':float(a.corr(b,method='spearman')),
 'difference_pad1_minus_pad2':{'mean':float(diff.mean()),'median':float(diff.median()),'mae':float(diff.abs().mean()),'rmse':float(np.sqrt(np.mean(diff**2))),
  'p01':float(diff.quantile(.01)),'p05':float(diff.quantile(.05)),'p25':float(diff.quantile(.25)),'p75':float(diff.quantile(.75)),'p95':float(diff.quantile(.95)),'p99':float(diff.quantile(.99)),
  'abs_gt_50':int((diff.abs()>50).sum()),'abs_gt_100':int((diff.abs()>100).sum()),'abs_gt_200':int((diff.abs()>200).sum())},
 'ratio_pad1_over_pad2_when_pad2_gt_50':{'n':int(ratio.count()),'p05':float(ratio.quantile(.05)),'median':float(ratio.median()),'p95':float(ratio.quantile(.95))},
 'irradiance_bands':[compare_subset(refband==name,str(name)) for name in ['low <=50','medium >50 to 800','high >800']],
 'raw_vs_temperature_compensated':{PAD1_TC:{'n':int(sel_irr[[PAD1,PAD1_TC]].dropna().shape[0]),'pearson':float(sel_irr[PAD1].corr(sel_irr[PAD1_TC])),'median_difference':float((sel_irr[PAD1]-sel_irr[PAD1_TC]).median()),'mae':float((sel_irr[PAD1]-sel_irr[PAD1_TC]).abs().mean())},PAD2_TC:{'n':int(sel_irr[[PAD2,PAD2_TC]].dropna().shape[0]),'pearson':float(sel_irr[PAD2].corr(sel_irr[PAD2_TC])),'median_difference':float((sel_irr[PAD2]-sel_irr[PAD2_TC]).median()),'mae':float((sel_irr[PAD2]-sel_irr[PAD2_TC]).abs().mean())}}}

# Targeted windows: known April 27 plateau, plus top disagreement timestamps separated by at least an hour.
absdiff=diff.abs().dropna().sort_values(ascending=False)
centers=[pd.Timestamp('2025-04-27 15:30:00')]
for ts in absdiff.index:
    if all(abs((ts-c).total_seconds())>=3600 for c in centers):
        centers.append(ts)
    if len(centers)>=8:break
windows=[]
for c in centers:
    s=c-pd.Timedelta(minutes=30); e=c+pd.Timedelta(minutes=30)
    for ts,row in sel_irr.loc[s:e].iterrows():
        envrow=sel_env.loc[ts] if ts in sel_env.index else None
        windows.append({'center_timestamp':c.isoformat(),'timestamp':ts.isoformat(),PAD1:row[PAD1],PAD1_TC:row[PAD1_TC],PAD2:row[PAD2],PAD2_TC:row[PAD2_TC],
          'pad1_minus_pad2':row[PAD1]-row[PAD2],AMB:(envrow[AMB] if envrow is not None else None)})
pd.DataFrame(windows).to_csv(OUT/'poa_disagreement_windows.csv',index=False)
top_disagree=[]
for ts in absdiff.head(20).index:
    top_disagree.append({'timestamp':ts.isoformat(),PAD1:float(sel_irr.loc[ts,PAD1]),PAD2:float(sel_irr.loc[ts,PAD2]),'pad1_minus_pad2':float(diff.loc[ts]),'absolute_difference':float(absdiff.loc[ts]),'daylight_proxy':bool(daylight.loc[ts])})

# Temperature channel stats, flatlines, abrupt changes, pair comparisons, and weather/irradiance relationships.
temp_channels=[AMB,*MODULES]
temp_summaries={}
for c in temp_channels:
    x=sel_env[c]; d=x.diff(); consecutive=grid.to_series().diff()==pd.Timedelta(minutes=5); v=x.dropna()
    temp_summaries[c]={**summary(x),'below_minus50_c':int((x< -50).sum()),'above_100_c':int((x>100).sum()),
      'abs_step_gt_5c':int((d.abs().gt(5)&consecutive).sum()),'abs_step_gt_10c':int((d.abs().gt(10)&consecutive).sum()),'abs_step_gt_20c':int((d.abs().gt(20)&consecutive).sum()),
      'longest_constant_run':max(exact_runs(x,grid,min_count=2),key=lambda r:r['count'],default=None),
      'constant_runs_ge60min':exact_runs(x,grid,min_count=12)}
# Pull temperature and irradiance records for historical sensor relation analysis.
merged=pd.concat([sel_irr[[PAD1,PAD2]],sel_env[temp_channels]],axis=1)
relations={}
for c in MODULES:
    z=merged[[c,AMB,PAD2]].dropna()
    relations[c]={'n_common':int(len(z)),'module_vs_ambient_pearson':float(z[c].corr(z[AMB])) if len(z)>1 else None,
      'module_vs_pad2_poa_pearson':float(z[c].corr(z[PAD2])) if len(z)>1 else None,'median_module_minus_ambient_c':float((z[c]-z[AMB]).median()) if len(z) else None}
for a,b in [(MODULES[0],MODULES[1]),(MODULES[2],MODULES[3])]:
    z=merged[[a,b]].dropna(); relations[f'{a}__vs__{b}']={'n_common':int(len(z)),'pearson':float(z[a].corr(z[b])) if len(z)>1 else None,
      'spearman':float(z[a].corr(z[b],method='spearman')) if len(z)>1 else None,'median_difference':float((z[a]-z[b]).median()) if len(z) else None,'mae':float((z[a]-z[b]).abs().mean()) if len(z) else None}

# Sensor metadata absent from the actual approved source headers.
absent_ids={int(x['metric_id']) for x in absent}
# Ensure list contains all absent weather-related records.
# Load prior C2.2 feasibility; do not rebuild or change target/sample data.
c22=json.loads((ROOT/'ml/data/reports/pvdaq/9068/phase_c2_2/readiness_audit.json').read_text(encoding='utf-8'))
prior_samples=c22['forecast_sample_feasibility']['weather_informed_increment_24h_availability_only']

result={'scope':{'approved_objects':[IRR_PATH.name,ENV_PATH.name],'no_new_downloads':True,'system_id':9068,
 'timestamp_labels_timezone_naive':True,'source_interval_resolution_metadata':metadata['System'].get('data_time_resolution'),'channel_aggregation_is_avg_per_system_metadata':True,
 'metadata_source_id_populated_for_reviewed_channels':False,'note':'A timestamp label and 5-minute resolution do not establish when an aggregate became available to a real-time forecaster.'},
 'source_time_quality':{'irradiance_object':irr_time,'environment_object':env_time,'overlap_start':start.isoformat(),'overlap_end':end.isoformat()},
 'inventory_csv':'environment_channel_inventory.csv','metadata_environment_channels_absent_csv':'metadata_environment_channels_absent.csv','metadata_channels_absent':absent,
 'poa_summaries':poa_summaries,'poa_paired_sensor_comparison':paired,'poa_nonzero_plateau_runs_ge60min':plateaus,'top_20_paired_disagreements':top_disagree,
 'daylight_proxy_definition':'At least one numeric raw POA channel (pad 1 or pad 2) exceeds 50 W/m2; classification is a sensor-derived descriptive proxy, not solar-position truth.',
 'daily_coverage_file':'poa_daily_coverage.csv','monthly_coverage_file':'poa_monthly_coverage.csv','diagnostic_windows_file':'poa_disagreement_windows.csv',
 'temperature_summaries':temp_summaries,'temperature_relationships':relations,
 'availability_at_forecast_issue':{'measured_on_labels_are_timezone_naive':True,'source_interval_start_close_convention_for_other_instruments':None,
   'reporting_delay_documented':False,'operational_use_safe_by_issue_time':'unresolved for irradiance and environmental sensors; use only observations whose actual availability is confirmed. No future weather observations used.'},
 'prior_c2_2_availability_only_sample_counts':prior_samples,
 'candidate_weather_sample_counts_if_accepted':{'no_channels_accepted_as_A_in_this_audit':0,'conditional_pad2_raw_only':prior_samples['candidate_feature_set_poa_pad2_raw'],'conditional_pad2_raw_plus_ambient':prior_samples['availability_only_poa_pad2_plus_ambient'],'conditional_pad2_raw_plus_ambient_plus_three_panel_temperatures':prior_samples['availability_only_poa_pad2_plus_ambient_plus_three_module_channels'],'target_only_baseline_from_c2_2':c22['forecast_sample_feasibility']['target_only_24h_lookback_samples']},
 'feature_acceptance':{
   PAD1:{'class':'REJECT','reason':'recurrent nonzero flatlines and large daylight disagreement with Pad 2'},
   PAD1_TC:{'class':'REJECT','reason':'near-duplicate of Pad 1 raw with the same plateau concern'},
   PAD2:{'class':'CONDITIONAL','reason':'best POA candidate, but no independent reference and availability timing unresolved'},
   PAD2_TC:{'class':'CONDITIONAL','reason':'near-duplicate of Pad 2 raw; do not use as an independent feature'},
   AMB:{'class':'CONDITIONAL','reason':'plausible range, but long stale run, missingness and issue-time availability unresolved'},
   MODULES[0]:{'class':'CONDITIONAL','reason':'plausible range/relationship, but multi-hour flatline and timing need review'},
   MODULES[1]:{'class':'CONDITIONAL','reason':'plausible range/relationship, but multi-hour flatline and timing need review'},
   MODULES[2]:{'class':'REJECT','reason':'3276.7 C dominates increment and is constant through April pilot'},
   MODULES[3]:{'class':'CONDITIONAL','reason':'plausible range/relationship, but multi-hour flatline and timing need review'},
   'inverter_temperature_metrics_149739_149826':{'class':'NOT_ACCEPTED_AS_WEATHER','reason':'operational inverter telemetry; separate timing/leakage review required'},
   'wind_metrics_149732_149738':{'class':'UNAVAILABLE','reason':'listed in metadata but absent from approved source objects'}},
 'decision':'B - weather channels remain conditional; target-only baseline is the recommended initial feature scope.'}
(OUT/'weather_sensor_quality_audit.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps({'irr_time':irr_time,'env_time':env_time,'inventory_rows':len(inventory),'metadata_absent_count':len(absent),'metadata_absent':[x['metric_id'] for x in absent],
 'pad1':poa_summaries[PAD1],'pad2':poa_summaries[PAD2],'pair':paired,'plateaus':plateaus,
 'temperatures':{c:{k:v for k,v in s.items() if k in ['numeric_observations','missing_pct_expected_grid','min','mean','median','max','negative_count','longest_constant_run','above_100_c','abs_step_gt_10c']} for c,s in temp_summaries.items()},
 'relations':relations,'prior_samples':prior_samples},indent=2,default=str))
