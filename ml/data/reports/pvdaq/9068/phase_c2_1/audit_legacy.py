import json, math
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

root=Path('.')
raw_dir=root/'ml/data/raw/pvdaq/9068/source_objects'
report_dir=root/'ml/data/reports/pvdaq/9068/phase_c2_1'
legacy=raw_dir/'9068_ac_power_data.csv'
increment=raw_dir/'9068_ac_power_data_20240101_20250430.csv'
channels=['inverter_1_ac_power_(kw)_inv_150143','inverter_2_ac_power_(kw)_inv_150144']
all_module=[f'inverter_module_{grp}.{n}_ac_power_(kw)_inv_{mid}' for grp,base in [(1,150135),(2,150139)] for n,mid in enumerate(range(base,base+4),1)]

def js(v):
    if pd.isna(v): return None
    if hasattr(v,'item'): v=v.item()
    if isinstance(v,(pd.Timestamp,)): return v.isoformat()
    return v

def runs(series, timestamps, min_len=12):
    vals=series.tolist(); ts=timestamps.tolist(); out=[]; start=0
    for i in range(1,len(vals)+1):
        if i==len(vals) or pd.isna(vals[start]) or pd.isna(vals[i]) or vals[i]!=vals[start]:
            n=i-start
            if n>=min_len and not pd.isna(vals[start]):
                out.append({'value':js(vals[start]),'count':n,'start':js(ts[start]),'end':js(ts[i-1]),'elapsed_between_endpoints_minutes': (ts[i-1]-ts[start]).total_seconds()/60 if not pd.isna(ts[start]) and not pd.isna(ts[i-1]) else None})
            start=i
    return out

def missing_runs(series, timestamps, min_len=12):
    mask=series.isna().tolist(); ts=timestamps.tolist(); out=[]; start=0
    for i in range(1,len(mask)+1):
        if i==len(mask) or mask[i]!=mask[start]:
            n=i-start
            if mask[start] and n>=min_len:
                out.append({'count':n,'start':js(ts[start]),'end':js(ts[i-1]),'elapsed_between_endpoints_minutes': (ts[i-1]-ts[start]).total_seconds()/60 if not pd.isna(ts[start]) and not pd.isna(ts[i-1]) else None})
            start=i
    return out

def summarize(df, label):
    out={'n_rows':int(len(df))}
    for c in [*channels,'total_inverter_ac_power_kw']:
        if c not in df: continue
        x=df[c]
        valid=x.dropna()
        diff=x.diff().abs().dropna()
        out[c]={
          'nonmissing':int(x.notna().sum()),'missing':int(x.isna().sum()),'missing_pct':float(x.isna().mean()*100),
          'first_nonmissing_timestamp':js(df.loc[x.notna(),'_ts'].min()) if x.notna().any() else None,
          'last_nonmissing_timestamp':js(df.loc[x.notna(),'_ts'].max()) if x.notna().any() else None,
          'negative_count':int((x<0).sum()),'zero_count':int((x==0).sum()),
          'min':js(valid.min()) if len(valid) else None,'max':js(valid.max()) if len(valid) else None,
          'mean':js(valid.mean()) if len(valid) else None,'median':js(valid.median()) if len(valid) else None,
          'percentiles':{str(q):js(valid.quantile(q)) for q in [0.01,.05,.25,.5,.75,.95,.99]} if len(valid) else {},
          'above_1910_kw_count':int((x>1910).sum()) if c in channels else None,
          'absolute_step_gt_500_kw_count':int((diff>500).sum()),'absolute_step_gt_1000_kw_count':int((diff>1000).sum()),
          'long_constant_runs_min_12':runs(x,df['_ts'],12),
          'longest_constant_run_min_12':max(runs(x,df['_ts'],12),key=lambda z:z['count'],default=None),
          'long_missing_runs_min_12':missing_runs(x,df['_ts'],12),
          'longest_missing_run_min_12':max(missing_runs(x,df['_ts'],12),key=lambda z:z['count'],default=None)
        }
    return out

# Header-only schema comparison; do not load unrelated fields into working frames.
legacy_header=pd.read_csv(legacy,nrows=0).columns.tolist()
inc_header=pd.read_csv(increment,nrows=0).columns.tolist()
# Load just original timestamp text and primary channels.
use=['measured_on',*channels]
ld_raw=pd.read_csv(legacy,usecols=use,dtype={c:'string' for c in use})
ld=ld_raw.copy()
legacy_source_rows=len(ld)
ld['_ts']=pd.to_datetime(ld['measured_on'],errors='coerce')
for c in channels: ld[c]=pd.to_numeric(ld[c],errors='coerce')
# Preserve raw timestamp and values/row order in derived target-only dataset.
ld['total_inverter_ac_power_kw']=ld[channels].sum(axis=1,min_count=2)
derived=ld_raw[['measured_on',*channels]].copy()
derived['total_inverter_ac_power_kw']=ld['total_inverter_ac_power_kw']
derived.to_csv(report_dir/'legacy_primary_inverter_history.csv',index=False)

# Timestamp audit.
ts=ld['_ts']; valid_ts=ts.dropna(); deltas=valid_ts.diff().dropna(); unique_ts=valid_ts.nunique(); dup_excess=int(valid_ts.duplicated().sum())
origin=valid_ts.min() if len(valid_ts) else pd.NaT
on_grid=((valid_ts-origin).dt.total_seconds()%300==0) if len(valid_ts) else pd.Series(dtype=bool)
expected_grid=int((valid_ts.max()-origin).total_seconds()//300+1) if len(valid_ts) else 0
cadence_counts=deltas.value_counts().sort_index()
gaps=deltas[deltas>pd.Timedelta(minutes=5)]
# Ordered row deltas, including duplicates/backwards, use all valid timestamps in original row order.
row_deltas=ts.diff()
# Extract dates and summarize last/first records.
ld_valid=ld.loc[ts.notna()].copy()
lastn=ld_valid.tail(24); firstinc=pd.read_csv(increment,usecols=use,dtype={'measured_on':'string'})
firstinc['_ts']=pd.to_datetime(firstinc['measured_on'],errors='coerce')
for c in channels: firstinc[c]=pd.to_numeric(firstinc[c],errors='coerce')
firstinc['total_inverter_ac_power_kw']=firstinc[channels].sum(axis=1,min_count=2)
inc_ts=firstinc['_ts'].dropna(); legacy_first=valid_ts.min(); legacy_last=valid_ts.max(); increment_first=inc_ts.min(); increment_last=inc_ts.max()
last_valid_target_ts=ld.loc[ld[channels].notna().all(axis=1),'_ts'].max()
overlap=sorted(set(valid_ts.dropna()).intersection(set(inc_ts.dropna())))
elapsed=(increment_first-legacy_last) if pd.notna(legacy_last) and pd.notna(increment_first) else None
missing_five_min_ticks=(int(elapsed.total_seconds()//300)-1) if elapsed is not None and elapsed>pd.Timedelta(minutes=5) else 0
valid_elapsed=(increment_first-last_valid_target_ts) if pd.notna(last_valid_target_ts) and pd.notna(increment_first) else None
missing_ticks_from_valid=(int(valid_elapsed.total_seconds()//300)-1) if valid_elapsed is not None and valid_elapsed>pd.Timedelta(minutes=5) else 0
# Actual interval delta distribution in increment and April subset.
inc_deltas=inc_ts.diff().dropna()
inc_nonfive=inc_deltas[inc_deltas!=pd.Timedelta(minutes=5)]
inc_gap_records=[]
for i in inc_nonfive.index:
    before=inc_ts.iloc[i-1]; after=inc_ts.iloc[i]; delta=inc_ts.iloc[i]-inc_ts.iloc[i-1]
    inc_gap_records.append({'previous_timestamp':js(before),'next_timestamp':js(after),'elapsed_minutes':delta.total_seconds()/60,
      'omitted_5m_labels_estimate':max(0,int(delta.total_seconds()//300)-1)})
inc_apr=firstinc.loc[(firstinc['_ts']>=pd.Timestamp('2025-04-01'))&(firstinc['_ts']<pd.Timestamp('2025-05-01'))].copy()
legacy_summary=summarize(ld,'legacy')
inc_summary=summarize(firstinc,'increment')
apr_summary=summarize(inc_apr,'april_2025')
# Yearly summaries permit detection of broad level/range shifts without declaring a cause.
yearly=[]
for year,g in ld_valid.groupby(ld_valid['_ts'].dt.year):
 row={'year':int(year),'rows':int(len(g)),'first':js(g['_ts'].min()),'last':js(g['_ts'].max())}
 for c in channels:
  x=g[c]; v=x.dropna(); row[c]={'valid':int(x.notna().sum()),'missing_pct':float(x.isna().mean()*100),'negative':int((x<0).sum()),'zero':int((x==0).sum()),'min':js(v.min()) if len(v) else None,'p50':js(v.median()) if len(v) else None,'p95':js(v.quantile(.95)) if len(v) else None,'p99':js(v.quantile(.99)) if len(v) else None,'max':js(v.max()) if len(v) else None,'above_1910':int((x>1910).sum())}
 yearly.append(row)
# Last/first boundary samples preserve exact source labels.
boundary={'legacy_last_24':lastn[['measured_on',*channels,'total_inverter_ac_power_kw']].to_dict(orient='records'),
          'increment_first_24':firstinc.head(24)[['measured_on',*channels,'total_inverter_ac_power_kw']].to_dict(orient='records')}
for key in ['legacy_last_24','increment_first_24']:
 for row in boundary[key]:
  for k,v in list(row.items()): row[k]=js(v)
# Explicit primary-target missingness check.
legacy_both=int(ld[channels].notna().all(axis=1).sum())
legacy_target=int(ld['total_inverter_ac_power_kw'].notna().sum())
# Other columns/header metrics.
report={
 'source':str(legacy),'system_id':9068,
 'schema':{'legacy_header':legacy_header,'increment_header':inc_header,'exact_header_match':legacy_header==inc_header,
   'legacy_only_columns':[c for c in legacy_header if c not in inc_header], 'increment_only_columns':[c for c in inc_header if c not in legacy_header],
   'timestamp_column_legacy':'measured_on','timestamp_column_increment':'measured_on','module_metrics_present_150135_150142':{c:(c in legacy_header) for c in all_module},
   'primary_metrics_present':{c:(c in legacy_header) for c in channels}},
 'legacy_quality':{'source_rows':legacy_source_rows,'timestamp_parse_failures':int(ts.isna().sum()),'first_timestamp':js(legacy_first),'last_timestamp':js(legacy_last),
   'duplicate_timestamp_excess_rows':dup_excess,'unique_valid_timestamps':int(unique_ts),'nonmonotonic_negative_deltas':int((row_deltas< pd.Timedelta(0)).sum()),
   'zero_deltas_duplicates':int((row_deltas==pd.Timedelta(0)).sum()),'monotonic_non_decreasing':bool(ts.dropna().is_monotonic_increasing),
   'cadence_delta_counts_seconds':{str(int(k.total_seconds())):int(v) for k,v in cadence_counts.items()},
   'five_minute_delta_count':int((deltas==pd.Timedelta(minutes=5)).sum()),'other_delta_count':int((deltas!=pd.Timedelta(minutes=5)).sum()),
   'max_delta_seconds':int(deltas.max().total_seconds()) if len(deltas) else None,'gap_count_gt_5m':int(len(gaps)),
   'largest_gaps': [{'start':js(valid_ts.iloc[int(i)]),'end':js(valid_ts.iloc[int(i)+1]),'minutes':float(gap.total_seconds()/60)} for i,gap in enumerate(deltas.tolist()) if gap>pd.Timedelta(minutes=5)][:30],
   'timestamps_on_five_minute_grid_from_first':int(on_grid.sum()) if hasattr(on_grid,'sum') else 0,'timestamps_off_grid_count':int((~on_grid).sum()) if hasattr(on_grid,'sum') else 0,
   'expected_5m_grid_points_in_span':expected_grid,'missing_5m_grid_points_by_unique_timestamp_count':max(0,expected_grid-int(unique_ts)),
   'channel_summary':legacy_summary,'combined_nonmissing':legacy_target,'combined_missing':int(len(ld)-legacy_target),
   'both_channels_nonmissing':legacy_both,'combined_equals_both_complete':legacy_target==legacy_both},
 'increment_quality':{'source_rows':int(len(firstinc)),'timestamp_parse_failures':int(firstinc['_ts'].isna().sum()),'first_timestamp':js(increment_first),'last_timestamp':js(increment_last),
   'unique_timestamps':int(inc_ts.nunique()),'duplicate_timestamps':int(inc_ts.duplicated().sum()),'nonmonotonic_deltas':int((firstinc['_ts'].diff()<pd.Timedelta(0)).sum()),
   'five_minute_delta_count':int((inc_deltas==pd.Timedelta(minutes=5)).sum()),'other_delta_count':int((inc_deltas!=pd.Timedelta(minutes=5)).sum()),
   'non_five_minute_deltas':inc_gap_records,'estimated_omitted_5m_labels_across_nonfive_deltas':sum(x['omitted_5m_labels_estimate'] for x in inc_gap_records),
   'channel_summary':inc_summary},
 'april_2025_increment_slice':{'rows':int(len(inc_apr)),'first_timestamp':js(inc_apr['_ts'].min()),'last_timestamp':js(inc_apr['_ts'].max()),
   'five_minute_delta_count':int((inc_apr['_ts'].diff()==pd.Timedelta(minutes=5)).sum()),'other_delta_count':int((inc_apr['_ts'].diff().dropna()!=pd.Timedelta(minutes=5)).sum()),'channel_summary':apr_summary},
 'continuity':{'legacy_last_timestamp':js(legacy_last),'last_valid_legacy_target_timestamp':js(last_valid_target_ts),'increment_first_timestamp':js(increment_first),'elapsed_legacy_end_to_increment_start_seconds':elapsed.total_seconds() if elapsed is not None else None,
   'elapsed_days':elapsed.total_seconds()/86400 if elapsed is not None else None,'overlapping_timestamps_count':len(overlap),'overlap_first':js(min(overlap)) if overlap else None,'overlap_last':js(max(overlap)) if overlap else None,
   'missing_5m_labels_strictly_between_source_endpoints':missing_five_min_ticks,'elapsed_last_valid_target_to_increment_start_seconds':valid_elapsed.total_seconds() if valid_elapsed is not None else None,
   'missing_5m_labels_strictly_between_last_valid_target_and_increment':missing_ticks_from_valid,'legacy_end_minus_metadata_endpoint_minutes':((legacy_last-pd.Timestamp('2023-11-16 13:45:00')).total_seconds()/60 if pd.notna(legacy_last) else None),
   'legacy_last_24_and_increment_first_24':boundary},
 'yearly_primary_summary':yearly,
 'source_limitations':['No external irradiance/environment/meter objects were acquired in this phase.','Matching metric names do not by themselves prove unchanged hardware or measurement boundary.']
}
(report_dir/'historical_continuity_audit.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps({'legacy_rows':legacy_source_rows,'legacy_first':str(legacy_first),'legacy_last':str(legacy_last),'parse_failures':int(ts.isna().sum()),'dups':dup_excess,'delta_counts':{str(k):int(v) for k,v in cadence_counts.items()},'missing':{c:int(ld[c].isna().sum()) for c in channels},'legacy_neg':{c:int((ld[c]<0).sum()) for c in channels},'legacy_zero':{c:int((ld[c]==0).sum()) for c in channels},'legacy_max':{c:js(ld[c].max()) for c in channels},'inc_first':str(increment_first),'inc_last':str(increment_last),'gap':str(elapsed),'overlap':len(overlap),'header_equal':legacy_header==inc_header,'legacy_only':[c for c in legacy_header if c not in inc_header],'increment_only':[c for c in inc_header if c not in legacy_header],'module_cols':[c for c in all_module if c in legacy_header]},indent=2))
