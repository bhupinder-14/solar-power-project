import json
from pathlib import Path
import pandas as pd
import numpy as np

ROOT=Path('.')
RAW=ROOT/'ml/data/raw/pvdaq/9068/source_objects'
OUT=ROOT/'ml/data/reports/pvdaq/9068/phase_c2_2'
P1='inverter_1_ac_power_(kw)_inv_150143'; P2='inverter_2_ac_power_(kw)_inv_150144'; TOTAL='total_inverter_ac_power_kw'
TGT=[P1,P2]
INC_AC=RAW/'9068_ac_power_data_20240101_20250430.csv'
LEGACY=RAW/'9068_ac_power_data.csv'
IRR=RAW/'9068_irradiance_data_20240101_20250430.csv'
ENV=RAW/'9068_environment_data_20240101_20250430.csv'
METER=RAW/'9068_meter_data_20240101_20250430.csv'
FEATURES={
 'POA pad 1 raw':'pyranometer_(class_a)_pad_1_poa_irradiance_(w/m2)_o_149723',
 'POA pad 1 temperature-compensated':'pyranometer_(class_a)_pad_1_poa_irradiance_temp_compensated_(w/m2)_o_149724',
 'POA pad 2 raw':'pyranometer_(class_a)_pad_2_poa_irradiance_(w/m2)_o_149725',
 'POA pad 2 temperature-compensated':'pyranometer_(class_a)_pad_2_poa_irradiance_temp_compensated_(w/m2)_o_149726',
 'Ambient temperature':'weather_station_ambient_temperature_(c)_o_149727',
 'Module temperature pad 1 sensor 1':'thermocouple_pad_1_back-of-module_temperature_1_(c)_o_149728',
 'Module temperature pad 1 sensor 2':'thermocouple_pad_1_back-of-module_temperature_2_(c)_o_149729',
 'Module temperature pad 2 sensor 2':'thermocouple_pad_2_back-of-module_temperature_2_(c)_o_149731',
 'Module temperature pad 2 sensor 1 (flagged failed)':'thermocouple_pad_2_back-of-module_temperature_1_(c)_o_149730',
 'Revenue-meter AC power (boundary/sign unresolved)':'meter_ac_power_(kw)_meter_150150',
}
WIND=['wind_sensor_max_wind_speed_(m/s)_o_149732','wind_sensor_wind_direction_o_149733','wind_sensor_wind_direction_compass_corr_o_149734','wind_sensor_wind_direction_fast_o_149735','wind_sensor_wind_speed_(m/s)_o_149736','wind_sensor_wind_speed_fast_(m/s)_o_149737','wind_sensor_wind_speed_std._dev._(m/s)_o_149738']


def read_group(path, cols):
    df=pd.read_csv(path,usecols=cols,dtype={c:'string' for c in cols})
    if 'measured_on' not in df: raise ValueError(f'measured_on missing: {path}')
    df['_ts']=pd.to_datetime(df['measured_on'],errors='coerce')
    for c in cols:
        if c!='measured_on': df[c]=pd.to_numeric(df[c],errors='coerce')
    return df

def runs(mask,index,object_name,period_type,source_mask=None,channel_masks=None):
    mask=np.asarray(mask,dtype=bool); records=[]; i=0
    while i<len(mask):
        if not mask[i]: i+=1; continue
        j=i+1
        while j<len(mask) and mask[j]: j+=1
        n=j-i; start=index[i]; end=index[j-1]
        if source_mask is not None:
            causes=[]
            if not np.all(np.asarray(source_mask[i:j],dtype=bool)): causes.append('source timestamp absent')
            if channel_masks is not None:
                for name,arr in channel_masks.items():
                    if np.any(np.asarray(arr[i:j],dtype=bool)): causes.append(name+' null in present row')
            cause='; '.join(dict.fromkeys(causes))
        else: cause=''
        records.append({'object':object_name,'period_type':period_type,'start_timestamp':start.isoformat(),'end_timestamp':end.isoformat(),'interval_count':int(n),'missing_duration_minutes':int(n*5),'elapsed_between_endpoint_labels_minutes':float((end-start).total_seconds()/60),'cause':cause})
        i=j
    return records

def summarize_runs(rs):
    thresholds=[15,60,360,1440,10080]
    return {'run_count':len(rs),'total_missing_intervals':int(sum(x['interval_count'] for x in rs)),
      'total_missing_minutes':int(sum(x['missing_duration_minutes'] for x in rs)),
      'longest_run':max(rs,key=lambda z:z['interval_count'],default=None),
      'run_counts_duration_gt_minutes':{str(t):sum(x['missing_duration_minutes']>t for x in rs) for t in thresholds}}

def build_target(path,obj):
    d=read_group(path,['measured_on',*TGT]); bad=int(d['_ts'].isna().sum()); d=d.loc[d['_ts'].notna()].copy()
    dup=int(d['_ts'].duplicated().sum()); d=d.drop_duplicates('_ts',keep='first')
    d=d.sort_values('_ts',kind='stable').set_index('_ts')
    start,end=d.index.min(),d.index.max(); grid=pd.date_range(start,end,freq='5min')
    g=d.reindex(grid); g.index.name='timestamp'; g['source_row_present']=g['measured_on'].notna()
    g[TOTAL]=g[[P1,P2]].sum(axis=1,min_count=2)
    g['p1_missing']=g[P1].isna(); g['p2_missing']=g[P2].isna(); g['target_missing']=g[TOTAL].isna()
    g['p1_missing_row']=g['source_row_present']&g['p1_missing']; g['p2_missing_row']=g['source_row_present']&g['p2_missing']
    g['both_null_row']=g['source_row_present']&g['p1_missing']&g['p2_missing']
    g['p1_only_null_row']=g['source_row_present']&g['p1_missing']&~g['p2_missing']
    g['p2_only_null_row']=g['source_row_present']&~g['p1_missing']&g['p2_missing']
    source_gaps=runs(~g['source_row_present'].to_numpy(),grid,obj,'source_timestamp_gap')
    p1null=runs(g['p1_missing_row'].to_numpy(),grid,obj,'inverter_1_null_existing_rows')
    p2null=runs(g['p2_missing_row'].to_numpy(),grid,obj,'inverter_2_null_existing_rows')
    paired_null_rows=runs((g['source_row_present']&g['target_missing']).to_numpy(),grid,obj,'paired_target_null_existing_rows')
    unavailable=runs(g['target_missing'].to_numpy(),grid,obj,'combined_target_unavailable_on_expected_grid',g['source_row_present'].to_numpy(),{'inverter_1':g['p1_missing'].to_numpy(),'inverter_2':g['p2_missing'].to_numpy()})
    dts=d.index.to_series().diff().dropna(); exact=int((dts==pd.Timedelta(minutes=5)).sum()); other=dts[dts!=pd.Timedelta(minutes=5)]
    timestamp_gap_records=[]
    for ts,delta in other.items():
        prev=d.index[d.index.get_loc(ts)-1]
        timestamp_gap_records.append({'object':obj,'previous_observed_timestamp':prev.isoformat(),'next_observed_timestamp':ts.isoformat(),'elapsed_minutes':delta.total_seconds()/60,'omitted_5m_grid_labels':max(0,int(delta.total_seconds()//300)-1)})
    p1n=int(g[P1].notna().sum()); p2n=int(g[P2].notna().sum()); pair=int(g[TOTAL].notna().sum()); rows=int(g['source_row_present'].sum())
    summary={'object':obj,'first_timestamp':start.isoformat(),'last_timestamp':end.isoformat(),'expected_5m_timestamps':len(grid),'actual_source_rows':rows,'missing_source_rows_on_grid':int((~g['source_row_present']).sum()),'timestamp_parse_failures':bad,'duplicate_timestamp_rows':dup,'numeric_inverter_1':p1n,'numeric_inverter_2':p2n,'paired_target_numeric':pair,
     'inverter_1_null_on_existing_rows':int(g['p1_missing_row'].sum()),'inverter_2_null_on_existing_rows':int(g['p2_missing_row'].sum()),'both_channels_null_on_existing_rows':int(g['both_null_row'].sum()),'only_inverter_1_null_existing_rows':int(g['p1_only_null_row'].sum()),'only_inverter_2_null_existing_rows':int(g['p2_only_null_row'].sum()),
     'combined_target_missing_on_expected_grid':int(g['target_missing'].sum()),'inverter_1_missing_pct_of_expected_grid':float(g[P1].isna().mean()*100),'inverter_2_missing_pct_of_expected_grid':float(g[P2].isna().mean()*100),'combined_target_missing_pct_of_expected_grid':float(g[TOTAL].isna().mean()*100),
     'adjacent_source_delta_5m_count':exact,'adjacent_source_delta_other_count':int(len(other)),'timestamp_gap_records':timestamp_gap_records,
     'source_timestamp_gap_runs':summarize_runs(source_gaps),'inverter_1_null_runs_existing_rows':summarize_runs(p1null),'inverter_2_null_runs_existing_rows':summarize_runs(p2null),'paired_target_null_runs_existing_rows':summarize_runs(paired_null_rows),'target_unavailable_runs_on_grid':summarize_runs(unavailable)}
    missing_periods=source_gaps+p1null+p2null+paired_null_rows+unavailable
    return g,summary,missing_periods

def get_segments(g,obj):
    valid=g[TOTAL].notna().to_numpy(); idx=g.index; out=[]; i=0
    while i<len(valid):
        if not valid[i]: i+=1; continue
        j=i+1
        while j<len(valid) and valid[j]: j+=1
        n=j-i; start=idx[i]; end=idx[j-1]
        out.append({'object':obj,'segment_id':f'{obj}_{len(out)+1:05d}','start_timestamp':start.isoformat(),'end_timestamp':end.isoformat(),'expected_5m_intervals':n,'valid_paired_observations':n,'missingness_pct_within_segment':0.0,'elapsed_label_span_minutes':float((end-start).total_seconds()/60),'span_days_by_interval_count':n*5/1440})
        i=j
    return out

def feature_summary(path, feature, target_grid, object_name, source_name):
    if feature not in pd.read_csv(path,nrows=0).columns:
        return {'feature':feature,'source':source_name,'status':'not present in approved object','source_rows':0,'numeric_observations':0,'source_missingness_pct':None,'first_numeric_timestamp':None,'last_numeric_timestamp':None,'cadence':'unavailable','target_timestamp_overlap_numeric':0,'target_overlap_missing_pct':100.0}
    d=read_group(path,['measured_on',feature]); n=len(d); parse=int(d['_ts'].isna().sum()); d=d.loc[d['_ts'].notna()]
    dup_count=int(d['_ts'].duplicated().sum())
    d=d.drop_duplicates('_ts',keep='first').set_index('_ts').sort_index()
    vals=d[feature]; deltas=d.index.to_series().diff().dropna();
    aligned=vals.reindex(target_grid.index)
    target_present=target_grid['source_row_present'].to_numpy()
    overlap_numeric=int((target_present & aligned.notna().to_numpy()).sum())
    target_rows=int(target_present.sum())
    # Feature completeness on the full expected target grid, including rows missing in the AC object.
    complete_grid=int(aligned.notna().sum())
    return {'feature':feature,'source':source_name,'status':'present','source_rows':n,'timestamp_parse_failures':parse,'numeric_observations':int(vals.notna().sum()),'source_null_values':int(vals.isna().sum()),'source_missingness_pct':float(vals.isna().mean()*100) if n else None,
      'first_numeric_timestamp':vals.dropna().index.min().isoformat() if vals.notna().any() else None,'last_numeric_timestamp':vals.dropna().index.max().isoformat() if vals.notna().any() else None,
      'source_unique_timestamps':int(d.index.nunique()),'source_duplicate_timestamps':dup_count,'source_5m_adjacent_deltas':int((deltas==pd.Timedelta(minutes=5)).sum()),'source_non5m_adjacent_deltas':int((deltas!=pd.Timedelta(minutes=5)).sum()),
      'numeric_values_on_target_source_timestamps':overlap_numeric,'target_source_rows':target_rows,'missingness_on_target_source_timestamps_pct':float((target_rows-overlap_numeric)/target_rows*100) if target_rows else None,
      'numeric_values_on_target_expected_grid':complete_grid,'target_expected_grid_timestamps':len(target_grid),'missingness_on_target_expected_grid_pct':float((len(target_grid)-complete_grid)/len(target_grid)*100) if len(target_grid) else None,
      'note':'Timestamp-label exact match; no timezone conversion or imputation.'}

legacy_grid,legacy_summary,legacy_missing=build_target(LEGACY,'legacy')
inc_grid,inc_summary,inc_missing=build_target(INC_AC,'increment')
segments=get_segments(legacy_grid,'legacy')+get_segments(inc_grid,'increment')
segdf=pd.DataFrame(segments)
segdf.to_csv(OUT/'target_segments.csv',index=False)
missdf=pd.DataFrame(legacy_missing+inc_missing)
missdf.to_csv(OUT/'missing_periods.csv',index=False)
# Derived counts by period, with each object kept separate.
lookbacks={'24h':288,'7d':2016,'30d':8640}; horizon_offset=4
lookback_summary={}
for label,L in lookbacks.items():
    relevant=segdf[segdf['expected_5m_intervals']>=L+horizon_offset]
    counts=[max(0,int(n)-L+1-horizon_offset) for n in relevant['expected_5m_intervals']]
    lookback_summary[label]={'lookback_intervals':L,'required_horizon_offset_intervals':horizon_offset,'segment_count_with_at_least_one_sample':int(len(relevant)),
      'paired_target_forecast_samples':int(sum(counts)),'target_observations_in_segments_meeting_minimum':int(relevant['valid_paired_observations'].sum()),'longest_usable_segment_count':int(segdf['expected_5m_intervals'].max()),'longest_usable_segment_start':segdf.loc[segdf['expected_5m_intervals'].idxmax(),'start_timestamp'],'longest_usable_segment_end':segdf.loc[segdf['expected_5m_intervals'].idxmax(),'end_timestamp']}
    lookback_summary[label]['paired_target_forecast_samples_by_object']={o:int(sum(max(0,int(n)-L+1-horizon_offset) for n in segdf.loc[segdf.object==o,'expected_5m_intervals'])) for o in ['legacy','increment']}

# Candidate feature availability on the increment target grid.
irrcols=[FEATURES[x] for x in FEATURES if x.startswith('POA')]
envcols=[FEATURES[x] for x in FEATURES if ('temperature' in x.lower())]
# meter feature is in separate meter object.
feature_matrix=[]
for name,col in FEATURES.items():
    if col.startswith('pyranometer'): path=IRR; src='irradiance object'
    elif col.startswith('meter_'): path=METER; src='meter object'
    else: path=ENV; src='environment object'
    qa=('POA pad 1 had a 180-minute constant-value flag in April; requires sensor review.' if name.startswith('POA pad 1') else
        'No >60-minute constant run in April; small negative dark-offset values and documented POA shading/tracker-stall representativeness concerns remain. Conditional only.' if name.startswith('POA pad 2') else
        'Flagged in prior April audit for a 125-minute constant-value run; not cleared as a valid feature.' if name=='Ambient temperature' else
        'Flagged in prior April audit for a 90–120-minute constant-value run; not cleared as a valid feature.' if 'Module temperature' in name and 'flagged failed' not in name else
        'Prior April audit found constant 3276.7 C for all observed timestamps; failed/unusable, exclude pending separate evidence.' if 'flagged failed' in name else
        'Revenue-meter boundary and sign semantics remain unresolved; availability only, not a cleared model feature.')
    feature_matrix.append({'name':name,**feature_summary(path,col,inc_grid,'increment',src),'feature_quality_status':qa})
for col in WIND:
    feature_matrix.append({'name':'Wind sensor channel','feature':col,'source':'environment object','status':'listed in System metadata but absent from approved environment CSV','source_rows':0,'numeric_observations':0,'source_missingness_pct':None,'first_numeric_timestamp':None,'last_numeric_timestamp':None,'cadence':'unavailable','target_timestamp_overlap_numeric':0,'target_overlap_missing_pct':100.0,'feature_quality_status':'Unavailable in the approved source object.'})
# No weather objects were acquired with legacy; explicitly mark coverage period.
legacy_feature_note={'period':'legacy 2017-08-23 through 2023-11-16','weather_or_irradiance_objects_available':False,'note':'Legacy AC file includes meter and power-factor columns, but no irradiance/environment time-series object was acquired; weather-feature coverage is not present in the legacy history.'}
# Target-only forecast sample counts per target segment.
# Weather candidate availability: pad 2 raw POA only (has no reported long constant run in April), and availability-only diagnostics with ambient and module channels.
def count_samples_with_features(grid, feature_cols, L=288, offset=4):
    # Union all feature channels onto exact 5-minute target grid, no fill.
    feat_frames=[]
    source_specs=[]
    for col in feature_cols:
        path=IRR if col.startswith('pyranometer') else ENV
        f=read_group(path,['measured_on',col]).dropna(subset=['_ts']).drop_duplicates('_ts').set_index('_ts')[col]
        feat_frames.append(f.reindex(grid.index).notna().astype('int8').rename(col))
    all_feat=pd.concat(feat_frames,axis=1)
    target_ok=grid[TOTAL].notna().to_numpy(); source_ok=grid['source_row_present'].to_numpy()
    # Require L consecutive target observations and each selected feature at each of the L input labels.
    roll_target=pd.Series(target_ok.astype('int8')).rolling(L,min_periods=L).sum().to_numpy()==L
    roll_features=(all_feat.rolling(L,min_periods=L).sum().eq(L).all(axis=1).to_numpy())
    # To remain within one uninterrupted target segment, all intermediate target labels through target horizon must exist.
    if len(grid)>offset:
        future_target=np.zeros(len(grid),dtype=bool); future_target[:-offset]=target_ok[offset:]
    else: future_target=np.zeros(len(grid),dtype=bool)
    else_future=np.zeros(len(grid),dtype=bool)
    if len(grid)>offset: else_future[:-offset]=np.logical_and.reduce([target_ok[k:k+len(grid)-offset] for k in range(1,offset+1)])
    valid=roll_target & roll_features & else_future & future_target
    return int(valid.sum())

def target_sample_mask(grid, L=288, offset=4):
    y=grid[TOTAL].notna().to_numpy()
    past=pd.Series(y.astype('int8')).rolling(L,min_periods=L).sum().to_numpy()==L
    future=np.ones(len(y),dtype=bool)
    for k in range(1,offset+1):
        shifted=np.zeros(len(y),dtype=bool)
        if len(y)>k: shifted[:-k]=y[k:]
        future &= shifted
    return past & future

def per_year_samples(grid, mask, obj, kind):
    x=pd.DataFrame({'timestamp':grid.index,'valid':mask})
    x=x[x.valid]
    if x.empty: return []
    rows=[]
    for year,g in x.groupby(x.timestamp.dt.year):
        rows.append({'object':obj,'sample_type':kind,'year':int(year),'valid_samples':int(len(g)),'first_issue_interval_label':g.timestamp.min().isoformat(),'last_issue_interval_label':g.timestamp.max().isoformat()})
    return rows

poa2=FEATURES['POA pad 2 raw']
weather_sample_counts={'candidate_feature_set_poa_pad2_raw':count_samples_with_features(inc_grid,[poa2]),
 'availability_only_poa_pad2_plus_ambient':count_samples_with_features(inc_grid,[poa2,FEATURES['Ambient temperature']]),
 'availability_only_poa_pad2_plus_ambient_plus_three_module_channels':count_samples_with_features(inc_grid,[poa2,FEATURES['Ambient temperature'],FEATURES['Module temperature pad 1 sensor 1'],FEATURES['Module temperature pad 1 sensor 2'],FEATURES['Module temperature pad 2 sensor 2']])}
annual_samples=[]
for obj,grid in [('legacy',legacy_grid),('increment',inc_grid)]:
    mask=target_sample_mask(grid)
    annual_samples.extend(per_year_samples(grid,mask,obj,'target-only 24h lookback'))
inc_poa=pd.read_csv(IRR,usecols=['measured_on',poa2],dtype={'measured_on':'string'})
inc_poa['_ts']=pd.to_datetime(inc_poa['measured_on'],errors='coerce')
inc_poa[poa2]=pd.to_numeric(inc_poa[poa2],errors='coerce')
poa_series=inc_poa.dropna(subset=['_ts']).drop_duplicates('_ts').set_index('_ts')[poa2].reindex(inc_grid.index)
poa_hist_ok=poa_series.notna().astype('int8').rolling(288,min_periods=288).sum().eq(288).to_numpy()
weather_mask=target_sample_mask(inc_grid)&poa_hist_ok
annual_samples.extend(per_year_samples(inc_grid,weather_mask,'increment','candidate POA-pad2 weather informed 24h lookback'))
pd.DataFrame(annual_samples).to_csv(OUT/'annual_sample_availability.csv',index=False)

# Inter-object discontinuity; no stitching occurs.
last_valid_legacy=legacy_grid.index[legacy_grid[TOTAL].notna()][-1]
first_valid_inc=inc_grid.index[inc_grid[TOTAL].notna()][0]
inter_elapsed=first_valid_inc-last_valid_legacy
inter_missing_slots=int(inter_elapsed.total_seconds()//300)-1
# Target totals across object spans, excluding all inter-object grid positions.
combined_summary={'object_spans_kept_separate':True,'expected_5m_timestamps_sum_object_spans':legacy_summary['expected_5m_timestamps']+inc_summary['expected_5m_timestamps'],
 'actual_source_rows_sum_objects':legacy_summary['actual_source_rows']+inc_summary['actual_source_rows'],'paired_target_numeric_sum_objects':legacy_summary['paired_target_numeric']+inc_summary['paired_target_numeric'],
 'combined_missing_target_rows_within_existing_source_rows':legacy_summary['combined_target_missing_on_expected_grid']+int((inc_grid['source_row_present']&inc_grid[TOTAL].isna()).sum()),
 'absent_increment_timestamp_grid_labels':inc_summary['missing_source_rows_on_grid'],'inter_object_gap_missing_5m_labels':inter_missing_slots,
 'not_a_contiguous_total_coverage_span':True}
# Combined segments by length. Save all segments; provide concise counts by thresholds.
threshold_intervals={'24h':288,'7d':2016,'30d':8640}
segment_length_counts={k:{'segments_meeting_duration':int((segdf.expected_5m_intervals>=v).sum()),'sum_valid_observations_in_those_segments':int(segdf.loc[segdf.expected_5m_intervals>=v,'valid_paired_observations'].sum()),'by_object':{o:{'segment_count':int(((segdf.object==o)&(segdf.expected_5m_intervals>=v)).sum()),'valid_observations':int(segdf.loc[(segdf.object==o)&(segdf.expected_5m_intervals>=v),'valid_paired_observations'].sum())} for o in ['legacy','increment']}} for k,v in threshold_intervals.items()}
# Feature semantics / source-reported cautions from previous approved pilot report.
pilot_q=json.loads((ROOT/'ml/data/reports/pvdaq/9068/pilot_2025-04_audited/quality_report.json').read_text(encoding='utf-8-sig'))
feature_notes={'previous_pilot_quality_flags':pilot_q.get('quality_flags_not_applied_as_filters',{}),
 'wind_metadata_channels_absent_from_environment_object':WIND,
 'no_humidity_or_cloud_channels_in_environment_header':True,
 'poa_context':'April review flagged pad-1 channel constant for 180 minutes; current readings may be affected by array shading/tracker-stall representativeness concerns. Pad-2 raw POA had no >60-minute constant run in April but remains subject to POA-location/shading limitations.',
 'module_temperature_149730':'April pilot value was 3276.7 C, constant for the full observed April span; exclude as failed/unusable pending separate evidence.',
 'ambient_and_other_module_temperature':'Prior pilot review flags long constant runs for ambient and the other usable thermocouples; availability is reported but channels are not cleared as valid model inputs by this audit.'}

result={'scope':{'system_id':9068,'target_definition':f'{P1} + {P2}; only when both are numeric','forecast_interval_minutes':5,'horizon_minutes':15,'issue_target_alignment':'Each source label t represents an interval beginning at t. Issue time is t+5 (close of latest interval); target interval begins issue+15=t+20, i.e. row offset 4 from the latest observed interval label.','historical_lookback':'288 consecutive 5-minute observations ending at issue interval label t','future_intermediate_continuity':'For sample counts, require valid paired target labels at t+5,t+10,t+15,t+20 so no sample crosses a missing-target segment.'},
 'target_availability':{'legacy':legacy_summary,'increment':inc_summary,'object_spans_combined_not_stitched':combined_summary},
 'continuous_valid_target_segments':{'segment_count':len(segments),'by_object':{o:int((segdf.object==o).sum()) for o in ['legacy','increment']},'counts_and_history_by_minimum_duration':segment_length_counts,'longest_segment':segdf.loc[segdf.expected_5m_intervals.idxmax()].to_dict() if len(segdf) else None,
   'lookback_sample_feasibility':lookback_summary},
 'missing_periods_output':'missing_periods.csv','segment_inventory_output':'target_segments.csv',
 'inter_object_gap':{'last_paired_legacy_timestamp':last_valid_legacy.isoformat(),'first_paired_increment_timestamp':first_valid_inc.isoformat(),'elapsed':str(inter_elapsed),'missing_five_minute_labels':inter_missing_slots,'overlap':False},
 'forecast_sample_feasibility':{'target_only_24h_lookback_samples':lookback_summary['24h']['paired_target_forecast_samples'],'weather_informed_increment_24h_availability_only':weather_sample_counts,'candidate_poa_input':'Pad 2 raw POA only, conditional; weather samples are not model features or a training dataset.'},
 'annual_sample_availability':annual_samples,
 'feature_availability_matrix':feature_matrix,'legacy_feature_coverage':legacy_feature_note,'feature_quality_notes':feature_notes,
 'chronological_evaluation_recommendations':{'strategy_A_target_only':'Use the legacy and increment as separate time blocks; reserve later contiguous segments for validation/test, do not join across the 45d+ gap, and use only target histories known by issue time. Legacy data allows longer history but has no acquired weather time series.','strategy_B_weather_informed':'Restrict to increment dates with exact timestamp overlap between target and approved weather inputs. Use only observed covariates at or before issue time; never use future observed weather. Segment gaps and use chronological train/validation/test blocks within the increment. Weather overlap is only about 16 months and contains internal data gaps.','split_dates':'Not selected; derive after a reviewed segment inventory and sample counts; no random split.'},
 'readiness_assessment':{'target_available':'yes with notable missingness','long_contiguous_segments':'yes, but interrupted by channel null runs and timestamp gaps','historical_gap':'quantified and must remain explicit','weather_overlap':'available in increment only; sensor quality remains conditional','leakage_safe_chronological_test':'feasible in principle inside the increment, with lower sample count after feature availability and segment rules','decision':'B - partially ready; explicitly account for coverage and feature-quality issues before EDA/baseline development.'}}
(OUT/'readiness_audit.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
(OUT/'feature_availability.csv').write_text(pd.DataFrame(feature_matrix).to_csv(index=False),encoding='utf-8')
print(json.dumps({'legacy':{k:legacy_summary[k] for k in ['expected_5m_timestamps','actual_source_rows','numeric_inverter_1','numeric_inverter_2','paired_target_numeric','combined_target_missing_on_expected_grid']},'increment':{k:inc_summary[k] for k in ['expected_5m_timestamps','actual_source_rows','missing_source_rows_on_grid','numeric_inverter_1','numeric_inverter_2','paired_target_numeric','combined_target_missing_on_expected_grid','adjacent_source_delta_other_count']},'segments':segment_length_counts,'longest':result['continuous_valid_target_segments']['longest_segment'],'lookbacks':lookback_summary,'forecast_samples':weather_sample_counts,'inter_gap':result['inter_object_gap'],'feature_rows':len(feature_matrix)},indent=2,default=str))
