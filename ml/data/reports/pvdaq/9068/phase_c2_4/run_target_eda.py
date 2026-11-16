from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT=Path('.')
BASE=ROOT/'ml/data'
RAW=BASE/'raw/pvdaq/9068/source_objects'
OUT=BASE/'reports/pvdaq/9068/phase_c2_4'
OUT.mkdir(parents=True,exist_ok=True)
CHANNELS={'inverter_1_ac_power_kw':'inverter_1_ac_power_(kw)_inv_150143','inverter_2_ac_power_kw':'inverter_2_ac_power_(kw)_inv_150144'}
SOURCES={
 'legacy':RAW/'9068_ac_power_data.csv',
 'increment':RAW/'9068_ac_power_data_20240101_20250430.csv'
}

plt.rcParams.update({'figure.dpi':130,'savefig.dpi':160,'font.size':9})

def read_period(name,path):
    df=pd.read_csv(path,usecols=['measured_on',*CHANNELS.values()],low_memory=False)
    df['timestamp']=pd.to_datetime(df['measured_on'],errors='coerce')
    df=df.drop(columns='measured_on')
    for c in CHANNELS.values(): df[c]=pd.to_numeric(df[c],errors='coerce')
    df=df.set_index('timestamp').sort_index()
    # Preserve source time labels; target is valid only when both inverter values are numeric.
    df['total_inverter_ac_power_kw']=df[CHANNELS['inverter_1_ac_power_kw']]+df[CHANNELS['inverter_2_ac_power_kw']]
    df.loc[df[list(CHANNELS.values())].isna().any(axis=1),'total_inverter_ac_power_kw']=np.nan
    return df

def runs(mask, index, period, value=None):
    a=np.asarray(mask,dtype=bool); n=len(a); out=[]
    if n==0:return out
    # Runs require adjacent five-minute labels; all series are reindexed before this call.
    starts=np.flatnonzero(a & np.r_[True,~a[:-1]])
    for s in starts:
        e=s+1
        while e<n and a[e] and index[e]-index[e-1]==pd.Timedelta(minutes=5): e+=1
        count=e-s
        out.append({'period':period,'start':index[s].isoformat(),'end':index[e-1].isoformat(),'interval_count':count,
                    'elapsed_label_minutes':float((index[e-1]-index[s]).total_seconds()/60),
                    'duration_minutes':count*5,'value':float(value[s]) if value is not None and np.isfinite(value[s]) else None})
    return out

def target_stats(s):
    x=s.dropna(); q=x.quantile([.01,.05,.25,.75,.95,.99])
    n=len(x)
    return {'count':int(n),'mean_kw':float(x.mean()),'median_kw':float(x.median()),'std_kw_sample':float(x.std()),
      'min_kw':float(x.min()),'max_kw':float(x.max()),'percentiles_kw':{str(k):float(v) for k,v in q.items()},
      'negative_count':int((x<0).sum()),'negative_pct':float((x<0).mean()*100),
      'zero_count':int((x==0).sum()),'zero_pct':float((x==0).mean()*100),
      'positive_count':int((x>0).sum()),'positive_pct':float((x>0).mean()*100),
      'near_zero_abs_le_10_kw_count':int((x.abs()<=10).sum()),'near_zero_abs_le_10_kw_pct':float((x.abs()<=10).mean()*100)}

def segments_for(s,period):
    valid=s.notna().to_numpy(); idx=s.index; out=[]
    # Build contiguous valid target segments; never cross NaNs or time gaps.
    i=0
    while i<len(s):
        if not valid[i]: i+=1; continue
        j=i+1
        while j<len(s) and valid[j] and idx[j]-idx[j-1]==pd.Timedelta(minutes=5): j+=1
        out.append({'period':period,'start':idx[i].isoformat(),'end':idx[j-1].isoformat(),'interval_count':j-i,
                    'duration_hours':(j-i)*5/60,'missingness_pct':0.0})
        i=j
    return out

def acf_by_segments(s, lags):
    # Segment-demeaned covariance sums: no pair or mean calculation crosses a data gap.
    nums={lag:0.0 for lag in lags}; den=0.0; pairs={lag:0 for lag in lags}; segs=segments_for(s,'')
    for seg in segs:
        x=s.loc[pd.Timestamp(seg['start']):pd.Timestamp(seg['end'])].to_numpy(dtype=float)
        if len(x)<2: continue
        z=x-np.mean(x); den+=float(np.dot(z,z))
        for lag in lags:
            if len(z)>lag:
                nums[lag]+=float(np.dot(z[:-lag],z[lag:])) if lag else float(np.dot(z,z))
                pairs[lag]+=len(z)-lag
    return [{'lag_intervals':int(l),'lag_minutes':int(l*5),'pair_count':int(pairs[l]),'acf':float(nums[l]/den) if den else None} for l in lags],segs

def consecutive_gap_info(s):
    idx=s.index
    deltas=idx.to_series().diff()
    gaps=deltas[deltas>pd.Timedelta(minutes=5)]
    return [{'previous_timestamp':(ts-pd.Timedelta(minutes=delta.total_seconds()/60)).isoformat(),
             'next_timestamp':ts.isoformat(),'elapsed_minutes':float(delta.total_seconds()/60),
             'omitted_5m_labels':int(delta.total_seconds()/300)-1}
            for ts,delta in gaps.items()]

periods={k:read_period(k,v) for k,v in SOURCES.items()}
# Assertions against previous independent C2.2 counts; no source is changed.
expected={'legacy':613497,'increment':135791}
for name,df in periods.items():
    assert df.index.is_monotonic_increasing and not df.index.has_duplicates
    assert int(df['total_inverter_ac_power_kw'].notna().sum())==expected[name], (name,int(df['total_inverter_ac_power_kw'].notna().sum()))

stats={name:target_stats(df['total_inverter_ac_power_kw']) for name,df in periods.items()}
all_values=pd.concat([df['total_inverter_ac_power_kw'].dropna() for df in periods.values()])
stats['available_periods_combined_unstitched']=target_stats(all_values)
source_rows={name:{'source_rows':int(len(df)),'first_timestamp':df.index.min().isoformat(),'last_timestamp':df.index.max().isoformat(),
                   'paired_target_count':int(df['total_inverter_ac_power_kw'].notna().sum()),
                   'target_missing_existing_rows':int(df['total_inverter_ac_power_kw'].isna().sum()),
                   'target_missing_pct_existing_rows':float(df['total_inverter_ac_power_kw'].isna().mean()*100),
                   'target_calc_check_max_abs_diff_kw':0.0}
             for name,df in periods.items()}
# Persist independent channel/target statistics and basic provenance.
(OUT/'target_statistics.json').write_text(json.dumps({'target':'inverter 1 AC kW + inverter 2 AC kW; only when both numeric','periods':source_rows,'statistics':stats},indent=2,allow_nan=False),encoding='utf-8')

# A complete-grid representation is analysis-only; NaNs are retained, never filled.
segments={}; daily_parts=[]; hour_parts=[]; weekday_parts=[]; month_parts=[]; negative_runs=[]; zero_runs=[]; missing_runs=[]; constant_runs=[]; delta_summaries={}; gap_data={}
lagset=[1,2,3,6,12,36,72,144,288]
acf_rows=[]
for name,df in periods.items():
    s=df['total_inverter_ac_power_kw']
    grid=pd.date_range(s.index.min(),s.index.max(),freq='5min')
    sg=s.reindex(grid)
    segs=segments_for(sg,name); segments[name]=segs
    # Daily summaries: interval-average kW; observed-energy proxy = kW * 5/60 hours, not extrapolated across missing values.
    frame=pd.DataFrame({'target_kw':sg,'timestamp':grid})
    frame['date']=frame['timestamp'].dt.date
    for day,g in frame.groupby('date',sort=True):
        x=g.target_kw.dropna(); n=len(x)
        daily_parts.append({'period':name,'date':str(day),'expected_intervals':len(g),'valid_intervals':n,'coverage_pct':100*n/len(g),
          'mean_kw':float(x.mean()) if n else None,'max_kw':float(x.max()) if n else None,'min_kw':float(x.min()) if n else None,
          'observed_energy_proxy_kwh':float(x.sum()*5/60) if n else None})
    tmp=sg.to_frame('kw'); tmp['hour']=tmp.index.hour; tmp['weekday']=tmp.index.dayofweek; tmp['month']=tmp.index.month
    for h,g in tmp.groupby('hour'):
        x=g.kw.dropna(); hour_parts.append({'period':name,'hour_label_timezone_unknown':int(h),'n':len(x),'mean_kw':float(x.mean()),'median_kw':float(x.median()),'p95_kw':float(x.quantile(.95))})
    for w,g in tmp.groupby('weekday'):
        x=g.kw.dropna(); weekday_parts.append({'period':name,'weekday_index_monday0':int(w),'n':len(x),'mean_kw':float(x.mean()),'median_kw':float(x.median()),'p95_kw':float(x.quantile(.95))})
    for m,g in tmp.groupby('month'):
        x=g.kw.dropna(); month_parts.append({'period':name,'month_number':int(m),'n':len(x),'mean_kw':float(x.mean()),'median_kw':float(x.median()),'p95_kw':float(x.quantile(.95))})
    # Runs are based on full expected grid, so missing labels/values break runs.
    negative_runs += runs(sg.lt(0).fillna(False),grid,name,sg.to_numpy())
    zero_runs += runs(sg.eq(0).fillna(False),grid,name,sg.to_numpy())
    missing_runs += runs(sg.isna(),grid,name,sg.to_numpy())
    # Constant runs among consecutive nonmissing target samples; exact equality as recorded.
    x=sg.to_numpy(dtype=float); constmask=np.zeros(len(x),dtype=bool)
    for i in range(1,len(x)-1):
        constmask[i]=np.isfinite(x[i-1]) and x[i]==x[i-1] and np.isfinite(x[i+1]) and x[i]==x[i+1]
    # Convert exact constant value groups to runs separately.
    i=0
    while i<len(x):
        if not np.isfinite(x[i]): i+=1; continue
        j=i+1
        while j<len(x) and np.isfinite(x[j]) and x[j]==x[i] and grid[j]-grid[j-1]==pd.Timedelta(minutes=5): j+=1
        if j-i>=12:
            constant_runs.append({'period':name,'start':grid[i].isoformat(),'end':grid[j-1].isoformat(),'interval_count':j-i,'duration_minutes':(j-i)*5,'value_kw':float(x[i])})
        i=j
    # Consecutive-step diagnostics do not bridge gaps.
    delta=sg.diff(); consecutive=(sg.notna()&sg.shift().notna())
    delta=delta[consecutive]
    thresholds=[100,250,500,1000]
    delta_summaries[name]={'valid_adjacent_pairs':int(len(delta)),'abs_delta_gt_threshold_counts':{str(t):int((delta.abs()>t).sum()) for t in thresholds},
      'max_abs_5m_delta_kw':float(delta.abs().max()) if len(delta) else None,'p99_abs_5m_delta_kw':float(delta.abs().quantile(.99)) if len(delta) else None,
      'negative_to_positive_transitions':int(((sg.shift()<0)&(sg>0)&consecutive).sum()),'positive_to_negative_transitions':int(((sg.shift()>0)&(sg<0)&consecutive).sum())}
    acf,seglist=acf_by_segments(sg,lagset); 
    for r in acf: r['period']=name; acf_rows.append(r)
    gap_data[name]={'expected_grid_intervals':len(grid),'valid_target':int(sg.notna().sum()),'missing_target_grid_intervals':int(sg.isna().sum()),
      'source_timestamp_gaps':consecutive_gap_info(df['total_inverter_ac_power_kw']),'valid_segment_count':len(segs),
      'longest_valid_segment':max(segs,key=lambda r:r['interval_count']) if segs else None,
      'segments_with_at_least_24h':sum(x['interval_count']>=288 for x in segs),'segments_with_at_least_7d':sum(x['interval_count']>=2016 for x in segs),
      'segments_with_at_least_30d':sum(x['interval_count']>=8640 for x in segs),
      'target_missing_run_count':sum(r['period']==name for r in missing_runs),
      'target_missing_runs_over_15min':sum(r['period']==name and r['duration_minutes']>15 for r in missing_runs),
      'target_missing_runs_over_1h':sum(r['period']==name and r['duration_minutes']>60 for r in missing_runs),
      'longest_target_missing_run':max((r for r in missing_runs if r['period']==name),key=lambda r:r['interval_count'],default=None)}

pd.DataFrame(daily_parts).to_csv(OUT/'daily_target_summary.csv',index=False)
pd.DataFrame(hour_parts).to_csv(OUT/'hour_of_day_summary.csv',index=False)
pd.DataFrame(weekday_parts).to_csv(OUT/'day_of_week_summary.csv',index=False)
pd.DataFrame(month_parts).to_csv(OUT/'month_of_year_summary.csv',index=False)
pd.DataFrame([x for ss in segments.values() for x in ss]).to_csv(OUT/'valid_target_segments.csv',index=False)
pd.DataFrame(acf_rows).to_csv(OUT/'target_autocorrelation.csv',index=False)
pd.DataFrame(negative_runs).query('interval_count >= 2').to_csv(OUT/'negative_target_runs.csv',index=False)
pd.DataFrame(missing_runs).to_csv(OUT/'target_missing_runs.csv',index=False)
pd.DataFrame(zero_runs).query('interval_count >= 2').to_csv(OUT/'zero_target_runs.csv',index=False)
pd.DataFrame(constant_runs).to_csv(OUT/'constant_target_runs_ge60min.csv',index=False)

# Targeted statistical sample feasibility for each historical lookback; requires every historical row, all four future-path labels, and target label at t+20.
# t is the label of the latest interval available at issue time t+5; target label is row offset +4.
lookbacks={'15_min':3,'30_min':6,'1_hour':12,'3_hours':36,'6_hours':72,'12_hours':144,'24_hours':288,'24_hour_lag_exact':289,'48_hours':576,'7_days':2016,'30_days':8640}
feas=[]
for period,df in periods.items():
    s=df['total_inverter_ac_power_kw']; idx=s.index
    fullidx=pd.date_range(idx.min(),idx.max(),freq='5min'); y=s.reindex(fullidx).to_numpy(dtype=float); valid=np.isfinite(y)
    for label,L in lookbacks.items():
        n=0
        # Future trajectory rows +1..+4 are required to be present for retrospective sample eligibility,
        # consistent with the previously documented C2.2 feasibility convention.
        for i in range(L-1,len(y)-4):
            if valid[i-L+1:i+5].all(): n+=1
        feas.append({'period':period,'lookback':label,'lookback_intervals':L,'valid_examples':n})
pd.DataFrame(feas).to_csv(OUT/'lookback_sample_feasibility.csv',index=False)

# Simple outlier/transition summaries without deciding validity or removing observations.
anomaly={}
for name,df in periods.items():
    s=df['total_inverter_ac_power_kw']; x=s.dropna(); rating_exceed=None
    anomaly[name]={'negative_count':int((x<0).sum()),'negative_min_kw':float(x[x<0].min()) if (x<0).any() else None,
      'negative_max_kw':float(x[x<0].max()) if (x<0).any() else None,'zero_count':int((x==0).sum()),
      'above_3820_kw_count':int((x>3820).sum()),'above_3820_kw_max':float(x[x>3820].max()) if (x>3820).any() else None,
      'above_1_5x_p99_count':int((x>1.5*x.quantile(.99)).sum()),'step_summary':delta_summaries[name],
      'zero_run_count':sum(r['period']==name for r in zero_runs),'zero_runs_at_least_1h':sum(r['period']==name and r['duration_minutes']>=60 for r in zero_runs),
      'longest_zero_run':max((r for r in zero_runs if r['period']==name),key=lambda r:r['interval_count'],default=None),
      'constant_runs_at_least_1h':sum(r['period']==name for r in constant_runs),
      'low_output_le_50kw_to_above_50kw_transitions':int(((df['total_inverter_ac_power_kw'].shift()<=50)&(df['total_inverter_ac_power_kw']>50)&df['total_inverter_ac_power_kw'].notna()&df['total_inverter_ac_power_kw'].shift().notna()).sum()),
      'above_50kw_to_low_output_le_50kw_transitions':int(((df['total_inverter_ac_power_kw'].shift()>50)&(df['total_inverter_ac_power_kw']<=50)&df['total_inverter_ac_power_kw'].notna()&df['total_inverter_ac_power_kw'].shift().notna()).sum()),
      'negative_recorded_hour_counts':{str(int(h)):int(((df['total_inverter_ac_power_kw']<0)&(df.index.hour==h)).sum()) for h in range(24)}}

result={'target_definition':'total_inverter_ac_power_kw = inverter_1_ac_power_(kw)_inv_150143 + inverter_2_ac_power_(kw)_inv_150144 only when both are numeric; negatives and zeros retained.','source_periods':source_rows,
 'statistics':stats,'temporal_coverage_and_segments':gap_data,'anomaly_summary':anomaly,'autocorrelation_method':'For each lag, pairs are evaluated only within contiguous valid five-minute target segments. Each segment is demeaned separately; no gap crossing.','timezone':'Timezone semantics are unresolved; CSV labels are timezone-naive. Calendar summaries use the recorded label fields only.','daily_energy_proxy':'Sum of observed interval-average kW multiplied by 5/60 h; reported as observed-data proxy only, no gap imputation or extrapolation.','forecast_alignment':{'adopted_interval_convention':'source timestamp t labels the beginning of a 5-minute interval (existing C2.2 convention)','issue_time':'T = t + 5 minutes, after the latest fully observed interval','target_interval_start':'T + 15 minutes = t + 20 minutes (row offset +4)','target':'average combined inverter AC power over the five-minute interval beginning at target_interval_start','feature_cutoff':'only history available by T; no target interval or future values in features'},'lookback_sample_feasibility':feas,
 'uncertainties':['Timezone and daylight-saving semantics unresolved.','Actual source reporting latency and availability time unresolved.','Per-inverter AC ratings are 1910 kW in prior metadata review; the 3820 kW sum is a reference, not a proven aggregate operating ceiling.','Apparent extrema are not automatically invalid.'],
 'previous_audit_count_check':'Target paired counts independently match C2.2: legacy 613,497; increment 135,791.'}
(OUT/'target_only_eda_summary.json').write_text(json.dumps(result,indent=2,allow_nan=False,default=lambda o: o.item() if isinstance(o,np.generic) else str(o)),encoding='utf-8')

# ---------- Plots; periods always shown separately or explicitly labeled. ----------
colors={'legacy':'#1f77b4','increment':'#e87500'}
# Distribution: full target range and positive-only comparison; no trimming.
fig,axs=plt.subplots(2,2,figsize=(13,8))
for j,name in enumerate(['legacy','increment']):
    x=periods[name]['total_inverter_ac_power_kw'].dropna()
    axs[0,j].hist(x,bins=120,color=colors[name],alpha=.85)
    axs[0,j].set_title(f'{name.title()} — full range (n={len(x):,})'); axs[0,j].set_xlabel('Combined inverter AC power (kW)'); axs[0,j].set_ylabel('Intervals'); axs[0,j].grid(alpha=.2)
    xp=x[x>0]
    axs[1,j].hist(xp,bins=120,color=colors[name],alpha=.85)
    axs[1,j].set_title(f'{name.title()} — positive production values (n={len(xp):,})'); axs[1,j].set_xlabel('Combined inverter AC power (kW)'); axs[1,j].set_ylabel('Intervals'); axs[1,j].grid(alpha=.2)
fig.suptitle('Target distributions by source period (all values retained)'); fig.tight_layout(); fig.savefig(OUT/'target_distribution_histograms.png'); plt.close(fig)
# Box plot by source: raw scale and positive values.
fig,axs=plt.subplots(1,2,figsize=(10,5))
data=[periods[k]['total_inverter_ac_power_kw'].dropna().to_numpy() for k in ['legacy','increment']]
axs[0].boxplot(data,tick_labels=['Legacy','Increment'],showfliers=True,flierprops={'markersize':1.2,'alpha':0.15}); axs[0].set_title('Target range (all recorded points represented)'); axs[0].set_ylabel('Combined inverter AC power (kW)'); axs[0].grid(axis='y',alpha=.2)
pos=[x[x>0] for x in data]; axs[1].boxplot(pos,tick_labels=['Legacy','Increment'],showfliers=True,flierprops={'markersize':1.2,'alpha':0.15}); axs[1].set_title('Positive production values (all fliers shown)'); axs[1].set_ylabel('Combined inverter AC power (kW)'); axs[1].grid(axis='y',alpha=.2)
fig.suptitle('Distribution by source period; all boxplot fliers retained'); fig.tight_layout(); fig.savefig(OUT/'target_boxplots.png'); plt.close(fig)
# Near-zero / negative distribution as separate panels; bins retain signed values.
fig,axs=plt.subplots(1,2,figsize=(12,4.5))
for name in ['legacy','increment']:
 x=periods[name]['total_inverter_ac_power_kw'].dropna(); n=x[(x<0) | ((x>0)&(x<=10)) | (x==0)]
 axs[0].hist(n,bins=100,alpha=.55,label=name,color=colors[name])
 neg=x[x<0]; axs[1].hist(neg,bins=80,alpha=.55,label=name,color=colors[name])
axs[0].set_title('Negative, zero and small positive values (0–10 kW)'); axs[0].set_xlabel('Combined inverter AC power (kW)'); axs[0].set_ylabel('Intervals'); axs[1].set_title('Negative recorded values'); axs[1].set_xlabel('Combined inverter AC power (kW)'); axs[1].set_ylabel('Intervals')
for a in axs:a.legend();a.grid(alpha=.2)
fig.tight_layout();fig.savefig(OUT/'target_negative_near_zero.png');plt.close(fig)
# Daily time series separate panels, with observed coverage and energy proxy.
daily=pd.DataFrame(daily_parts); fig,axs=plt.subplots(2,1,figsize=(14,8),sharey=True)
for ax,name in zip(axs,['legacy','increment']):
 d=daily[daily.period==name].copy(); dates=pd.to_datetime(d.date)
 ax.plot(dates,d.mean_kw,label='Daily mean (kW)',lw=.8,color=colors[name]); ax.plot(dates,d.max_kw,label='Daily maximum (kW)',lw=.55,alpha=.65,color='black'); ax.set_title(name.title()); ax.set_ylabel('Power (kW)'); ax.legend(); ax.grid(alpha=.2)
fig.suptitle('Daily target behavior by source object; objects are not stitched');fig.tight_layout();fig.savefig(OUT/'daily_power_by_period.png');plt.close(fig)
# Daily observed energy proxy.
fig,axs=plt.subplots(2,1,figsize=(14,7),sharey=True)
for ax,name in zip(axs,['legacy','increment']):
 d=daily[daily.period==name];ax.plot(pd.to_datetime(d.date),d.observed_energy_proxy_kwh,color=colors[name],lw=.8);ax.set_title(name.title());ax.set_ylabel('Observed energy proxy (kWh)');ax.grid(alpha=.2)
fig.suptitle('Daily observed energy proxy (missing intervals are not filled)');fig.tight_layout();fig.savefig(OUT/'daily_energy_proxy.png');plt.close(fig)
# Cyclic descriptive summaries.
fig,axs=plt.subplots(1,3,figsize=(15,4.5))
for name in ['legacy','increment']:
 h=pd.DataFrame(hour_parts); w=pd.DataFrame(weekday_parts); m=pd.DataFrame(month_parts)
 axs[0].plot(h[h.period==name].hour_label_timezone_unknown,h[h.period==name].median_kw,marker='o',ms=2,label=name,color=colors[name])
 axs[1].plot(w[w.period==name].weekday_index_monday0,w[w.period==name].median_kw,marker='o',label=name,color=colors[name])
 axs[2].plot(m[m.period==name].month_number,m[m.period==name].median_kw,marker='o',label=name,color=colors[name])
axs[0].set_xlabel('Recorded timestamp hour (timezone unknown)');axs[1].set_xlabel('Day of week (Mon=0)');axs[2].set_xlabel('Month number')
for ax in axs:ax.set_ylabel('Median combined power (kW)');ax.grid(alpha=.2);ax.legend()
axs[0].set_title('Hour of day');axs[1].set_title('Day of week');axs[2].set_title('Month of year (periods separate)');fig.tight_layout();fig.savefig(OUT/'calendar_pattern_summaries.png');plt.close(fig)
# ACF plot, with clearly separated source period lines.
acfdf=pd.DataFrame(acf_rows);fig,ax=plt.subplots(figsize=(10,5))
for name in ['legacy','increment']:
 z=acfdf[acfdf.period==name];ax.plot(z.lag_minutes,z.acf,marker='o',label=name,color=colors[name])
ax.set_xscale('log');ax.set_xticks([5,10,15,30,60,180,360,720,1440]);ax.set_xticklabels(['5','10','15','30','60','180','360','720','1440']);ax.set_xlabel('Lag (minutes; log spacing)');ax.set_ylabel('Segment-demeaned autocorrelation');ax.set_title('Target autocorrelation within continuous valid segments');ax.grid(alpha=.25);ax.legend();fig.tight_layout();fig.savefig(OUT/'target_autocorrelation.png');plt.close(fig)
# Rolling means and standard deviations, on the first seven days of each longest valid segment.
fig,axs=plt.subplots(2,2,figsize=(14,8))
for row,name in enumerate(['legacy','increment']):
 long=max(segments[name],key=lambda z:z['interval_count']); s=periods[name]['total_inverter_ac_power_kw'].loc[pd.Timestamp(long['start']):pd.Timestamp(long['end'])]
 s=s.iloc[:min(len(s),7*288)]
 for hours,window in [(0.25,3),(1,12),(24,288)]:
  axs[row,0].plot(s.index,s.rolling(window,min_periods=window).mean(),label=f'{hours:g}h',lw=.8)
  axs[row,1].plot(s.index,s.rolling(window,min_periods=window).std(),label=f'{hours:g}h',lw=.8)
 axs[row,0].set_title(f'{name.title()} — trailing mean'); axs[row,1].set_title(f'{name.title()} — trailing standard deviation')
 for ax in axs[row]:ax.set_ylabel('kW');ax.legend(title='Window');ax.grid(alpha=.2)
axs[-1,0].set_xlabel('Recorded timestamp (timezone unknown)');axs[-1,1].set_xlabel('Recorded timestamp (timezone unknown)')
fig.suptitle('Right-aligned rolling statistics on valid continuous segments; no gaps crossed');fig.tight_layout();fig.savefig(OUT/'rolling_target_example.png');plt.close(fig)
# Monthly target availability by source, distinct from target nulls.
fig,ax=plt.subplots(figsize=(12,4.5))
for name,df in periods.items():
 s=df['total_inverter_ac_power_kw']; gi=pd.date_range(s.index.min(),s.index.max(),freq='5min'); tmp=s.reindex(gi).resample('MS').agg(['count','size']); cov=tmp['count']/tmp['size']*100
 ax.plot(cov.index,cov.values,marker='.',label=name,color=colors[name])
ax.set_xlabel('Recorded month label');ax.set_ylabel('Paired target availability (%)');ax.set_ylim(0,101);ax.set_title('Monthly paired-target availability within each object');ax.grid(alpha=.2);ax.legend();fig.tight_layout();fig.savefig(OUT/'monthly_target_availability.png');plt.close(fig)

# Optional PACF on each period's longest continuous segment; report method and failure gracefully.
pacf_result={'method':'statsmodels PACF on each period longest uninterrupted segment, capped at 24 hours of lags','available':False,'periods':{}}
try:
 from statsmodels.tsa.stattools import pacf
 pacf_result['available']=True
 for name in ['legacy','increment']:
  long=max(segments[name],key=lambda z:z['interval_count']); s=periods[name]['total_inverter_ac_power_kw'].loc[pd.Timestamp(long['start']):pd.Timestamp(long['end'])].to_numpy(dtype=float)
  maxlag=min(288,len(s)//2-1)
  vals=pacf(s,nlags=maxlag,method='ywm')
  pacf_result['periods'][name]={'segment_start':long['start'],'segment_end':long['end'],'segment_intervals':len(s),'max_lag_intervals':int(maxlag),'values':[float(x) for x in vals]}
 fig,axs=plt.subplots(2,1,figsize=(12,6))
 for ax,name in zip(axs,['legacy','increment']):
  z=pacf_result['periods'][name]; ax.stem(np.arange(1,len(z['values']))*5,z['values'][1:],basefmt=' ');ax.set_xlim(0,1440);ax.set_title(f'{name.title()} — longest continuous segment');ax.set_ylabel('Partial autocorrelation');ax.grid(alpha=.2)
 axs[-1].set_xlabel('Lag (minutes)');fig.suptitle('PACF on longest valid segment only (descriptive)');fig.tight_layout();fig.savefig(OUT/'target_partial_autocorrelation.png');plt.close(fig)
except Exception as e:
 pacf_result['error']=f'{type(e).__name__}: {e}'
(OUT/'partial_autocorrelation_summary.json').write_text(json.dumps(pacf_result,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps({'statistics':stats,'periods':source_rows,'gaps':gap_data,'anomaly':anomaly,'lookback_feasibility':feas,'acf':acf_rows,'pacf_available':pacf_result['available'],'outputs':sorted(p.name for p in OUT.iterdir())},indent=2,default=str))






