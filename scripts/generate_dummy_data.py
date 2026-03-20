"""
scripts/generate_dummy_data.py — 더미 고객 데이터 생성

실데이터 스키마(schema.md)와 동일한 구조의 CSV를 data/ 에 저장한다.
AI 파이프라인은 GET /api/v1/data/export?table=<name> 으로 가져간다.

실행: python scripts/generate_dummy_data.py
"""

import pandas as pd
import numpy as np
from pathlib import Path

rng = np.random.default_rng(42)

DATA_DIR    = Path(__file__).parent.parent / "data"
N_CUSTOMERS = 2000

# ──────────────────────────────────────────────
# 공통 참조 값
# ──────────────────────────────────────────────
AP2_REGIONS = ["SEA", "SEAU", "SEF", "SEG", "SEAS", "SEASA", "KOREA", "SECA", "SWA"]
AP2_WEIGHTS = [0.18, 0.10, 0.15, 0.08, 0.06, 0.07, 0.12, 0.08, 0.16]

COUNTRY_BY_AP2 = {
    "SEA":   ["United States"],
    "SEAU":  ["Australia", "Singapore", "Thailand", "Vietnam", "Malaysia"],
    "SEF":   ["France", "Spain", "Italy", "Netherlands", "Belgium"],
    "SEG":   ["Germany", "Switzerland"],
    "SEAS":  ["Austria", "Poland", "Czech Republic"],
    "SEASA": ["Brazil", "Mexico", "Argentina", "Colombia"],
    "KOREA": ["South Korea"],
    "SECA":  ["Canada"],
    "SWA":   ["India", "Pakistan", "Bangladesh"],
}
CNTY_CD_BY_AP2  = {"SEA":"USA","SEAU":"AUS","SEF":"FRA","SEG":"DEU","SEAS":"AUT","SEASA":"BRA","KOREA":"KOR","SECA":"CAN","SWA":"IND"}
CNTY_CD2_BY_AP2 = {"SEA":"US","SEAU":"AU","SEF":"FR","SEG":"DE","SEAS":"AT","SEASA":"BR","KOREA":"KR","SECA":"CA","SWA":"IN"}
GC_BY_AP2       = {"SEA":"N.America","SEAU":"S.E.Asia","SEF":"Europe","SEG":"Europe","SEAS":"Europe","SEASA":"L.America","KOREA":"KOREA","SECA":"N.America","SWA":"S.W.Asia"}
CURRENCIES_BY_AP2 = {"SEA":("USD",1.0),"SEAU":("AUD",1.52),"SEF":("EUR",0.92),"SEG":("EUR",0.92),"SEAS":("EUR",0.92),"SEASA":("BRL",5.0),"KOREA":("KRW",1320.0),"SECA":("CAD",1.36),"SWA":("INR",83.0)}

ACTIVENESS_LEVELS  = ["Active (1M)","Active (3M)","Active (6M)","Active (12M)","Inactive"]
ACTIVENESS_WEIGHTS = [0.25, 0.20, 0.18, 0.15, 0.22]

VOYAGER_SEGMENTS = ["Gamer","Premium Buyer","Health Enthusiast","Smart Home User","Budget Shopper","Early Adopter","Loyal Customer","Fashion Forward"]

# 카테고리별 제품: (마케팅명, 시리즈, SKU, pd_type, pd_rec_type, pd_rec_sub_type, pd_smart, 화면)
PRODUCTS_BY_CAT = {
    "HHP":     [("Galaxy S25 Ultra","S","SM-S938B","SMART","Smartphones","Galaxy_S","Y","6.9_UB"),
                ("Galaxy S25+","S","SM-S936B","SMART","Smartphones","Galaxy_S","Y","6.7_UB"),
                ("Galaxy A55","A","SM-A556B","SMART","Smartphones","Galaxy_A","Y","6.6_UB"),
                ("Galaxy A35","A","SM-A356B","SMART","Smartphones","Galaxy_A","Y","6.6_UB"),
                ("Galaxy Z Fold6","Z Fold","SM-F956B","FOLD","Foldables","Galaxy_Z_Fold","Y","7.6_UB"),
                ("Galaxy Z Flip6","Z Flip","SM-F741B","FLIP","Foldables","Galaxy_Z_Flip","Y","6.7_UB")],
    "WEARABLE":[("Galaxy Watch 7","Watch7","SM-L300N","WATCH","Watches","Galaxy_Watch","Y",None),
                ("Galaxy Watch Ultra","Watch Ultra","SM-L705N","WATCH","Watches","Galaxy_Watch","Y",None),
                ("Galaxy Buds3 Pro","Buds3","SM-R630N","BUDS","Earbuds","Galaxy_Buds","N",None),
                ("Galaxy Ring","Ring","SM-Q501N","RING","Wearables","Galaxy_Ring","N",None)],
    "TV":      [('Neo QLED 8K 85"',"Neo QLED","QA85QN900D","QLED","TVs","Neo_QLED","Y",'85"'),
                ('OLED 77"',"OLED","QA77S90D","OLED","TVs","OLED","Y",'77"'),
                ('Crystal UHD 65"',"Crystal UHD","UA65AU8000","UHD","TVs","Crystal_UHD","Y",'65"')],
    "TABLET":  [("Galaxy Tab S9 Ultra","Tab S9","SM-X916B","TABLET","Tablets","Galaxy_Tab_S","Y",'14.6"'),
                ("Galaxy Tab S9 FE","Tab S9 FE","SM-X516B","TABLET","Tablets","Galaxy_Tab_S","Y",'10.9"')],
    "PC":      [("Galaxy Book4 Pro","Book4","NP960XGK","LAPTOP","Laptops","Galaxy_Book","Y",'16"'),
                ("Galaxy Book4 360","Book4","NP730QGK","LAPTOP","Laptops","Galaxy_Book","Y",'13.3"')],
    "AUDIO":   [("Galaxy Buds2 Pro","Buds2","SM-R510N","BUDS","Earbuds","Galaxy_Buds","N",None),
                ("Sound Bar Q990D","Sound Bar","HW-Q990D","SOUNDBAR","Soundbars","Sound_Bar","Y",None)],
    "DA":      [("Bespoke AI Washer","Bespoke","WF25BB6900H","WASHER","Appliances","Bespoke_WM","Y",None),
                ("Bespoke French Door Fridge","Bespoke","RF29BB6200A","FRIDGE","Appliances","Bespoke_REF","Y",None)],
}

PD_CATS    = list(PRODUCTS_BY_CAT.keys())
PD_WEIGHTS = [0.40, 0.15, 0.12, 0.10, 0.08, 0.08, 0.07]
DIV_BY_CAT = {"HHP":"MX","WEARABLE":"MX","TABLET":"MX","PC":"MX","TV":"VD","AUDIO":"VD","DA":"DA"}
GRP_BY_CAT = {"HHP":"MOBILE","WEARABLE":"ME","TABLET":"TABLET","PC":"PC","TV":"TV","AUDIO":"AUDIO","DA":"DA"}

STORE_TYPES   = ["D2C","EPP","Retail","Carrier","Operator"]
STORE_WEIGHTS = [0.30, 0.15, 0.30, 0.15, 0.10]

SAMSUNG_APPS = [
    ("com.samsung.android.health","Samsung Health","HEALTH"),
    ("com.samsung.android.app.galaxyfinder","Galaxy Store","UTILITY"),
    ("com.samsung.android.messaging","Samsung Messages","UTILITY"),
    ("com.samsung.android.email.provider","Samsung Email","PRODUCTIVITY"),
    ("com.samsung.android.spay","Samsung Pay","FINANCE"),
    ("com.samsung.android.smartthings","SmartThings","UTILITY"),
]
NON_SAMSUNG_APPS = [
    ("com.facebook.katana","Facebook","SOCIAL"),("com.instagram.android","Instagram","SOCIAL"),
    ("com.google.android.youtube","YouTube","ENTERTAINMENT"),("com.supercell.hayday","Hay Day","GAME"),
    ("com.king.candycrushsaga","Candy Crush Saga","GAME"),("com.netflix.mediaclient","Netflix","ENTERTAINMENT"),
    ("com.spotify.music","Spotify","ENTERTAINMENT"),("com.amazon.mShop.android.shopping","Amazon Shopping","SHOPPING"),
    ("com.google.android.gm","Gmail","PRODUCTIVITY"),("com.whatsapp","WhatsApp","SOCIAL"),
    ("com.tiktok.android","TikTok","SOCIAL"),("com.twitter.android","X (Twitter)","SOCIAL"),
    ("com.kakao.talk","KakaoTalk","SOCIAL"),("com.garena.freefireth","Free Fire","GAME"),
    ("com.riotgames.league.wildrift","Wild Rift","GAME"),("com.paypal.android.p2pmobile","PayPal","FINANCE"),
    ("com.google.android.apps.maps","Google Maps","UTILITY"),
]

INTERESTS = ["ART & CUSTOMIZED","BANKING & FINANCE","ENTERTAINMENT & MEDIA","FASHION & BEAUTY",
             "FITNESS & WELLNESS","FOOD & BEVERAGE","GAMING","SMART HOME & IOT","SPORTS","TRAVEL & LEISURE"]


# ──────────────────────────────────────────────
# 생성 함수
# ──────────────────────────────────────────────
def gen_demo() -> pd.DataFrame:
    ap2      = rng.choice(AP2_REGIONS, N_CUSTOMERS, p=AP2_WEIGHTS)
    countries = [rng.choice(COUNTRY_BY_AP2[a]) for a in ap2]
    age_grp  = rng.choice([0,1,2], N_CUSTOMERS, p=[0.35,0.40,0.25])
    age      = np.where(age_grp==0, rng.integers(18,30,N_CUSTOMERS),
                np.where(age_grp==1, rng.integers(30,50,N_CUSTOMERS),
                         rng.integers(50,70,N_CUSTOMERS))).clip(18,75)
    voyager  = [str(list(rng.choice(VOYAGER_SEGMENTS, int(rng.integers(1,4)), replace=False)))
                for _ in range(N_CUSTOMERS)]
    return pd.DataFrame({
        "index": range(1, N_CUSTOMERS+1),
        "sa_activeness": rng.choice(ACTIVENESS_LEVELS, N_CUSTOMERS, p=ACTIVENESS_WEIGHTS),
        "usr_age": age, "usr_gndr": rng.choice(["M","F"], N_CUSTOMERS, p=[0.52,0.48]),
        "usr_cnty_name": countries, "usr_cnty_ap2": ap2,
        "relation_all_cnt": rng.integers(1,5,N_CUSTOMERS),
        "relation_family_group_cnt": rng.integers(0,3,N_CUSTOMERS),
        "relation_estimated_cnt": rng.integers(1,4,N_CUSTOMERS),
        "voyager_segment": voyager,
    })


def gen_clv(demo: pd.DataFrame) -> pd.DataFrame:
    n          = len(demo)
    age_arr    = demo["usr_age"].values
    active_arr = demo["sa_activeness"].str.startswith("Active").values.astype(float)
    age_fac    = 1 - (age_arr - 18) / 100
    act_fac    = active_arr * 0.2
    retention  = np.clip(age_fac*0.5 + act_fac + rng.uniform(0.2,0.5,n), 0.2, 0.99)
    ltv        = np.clip(rng.lognormal(7.5,1.2,n), 50, 50_000)
    pchs_cnt   = rng.integers(1,8,n)
    prem_cnt   = np.minimum(rng.integers(0,4,n), pchs_cnt)
    health_p   = np.clip(0.35 + age_fac*0.1, 0.1, 0.8)
    wallet_p   = np.clip(0.25 + act_fac*0.3, 0.1, 0.8)
    st_p       = np.clip(0.20 + prem_cnt/10, 0.1, 0.7)
    first_dt   = pd.to_datetime("2018-01-01") + pd.to_timedelta(rng.integers(0,2000,n), unit="D")
    cap        = pd.Timestamp("2025-03-01")
    last_dt    = pd.DatetimeIndex([min(d, cap) for d in first_dt + pd.to_timedelta(rng.integers(30,1800,n), unit="D")])
    prod_map   = rng.choice(["HHP","WATCH","TV","TABLET"], n, p=[0.5,0.2,0.2,0.1])
    return pd.DataFrame({
        "index": demo["index"].values, "bs_date": "2024-12-27",
        "gc":        [GC_BY_AP2[a]      for a in demo["usr_cnty_ap2"]],
        "cnty_cd":   [CNTY_CD_BY_AP2[a] for a in demo["usr_cnty_ap2"]],
        "subsidiary": demo["usr_cnty_ap2"].values, "gender": demo["usr_gndr"].values,
        "age": age_arr,
        "age_band": pd.cut(age_arr, bins=[0,29,39,49,59,100], labels=["20s","30s","40s","50s","60s+"]).astype(str),
        "product_mapping4": prod_map,
        "division_fin": np.where(np.isin(prod_map,["HHP","WATCH","TABLET"]),"MX","VD"),
        "retention_score": retention.round(3),
        "retention_adj": np.clip(retention * rng.uniform(0.8,1.0,n), 0.1, 0.99).round(3),
        "val_p": np.clip(rng.lognormal(6.5,1.0,n), 50, 20_000).round(2),
        "pchs_cnt": pchs_cnt, "div_cnt": rng.integers(1,4,n),
        "prod_cnt": rng.integers(1,6,n), "prod_cnt_bydiv": rng.integers(1,4,n),
        "prd_cyc_adj_y": rng.uniform(0.5,4.0,n).round(2), "pchs_cyc_org_y": rng.uniform(0.5,4.0,n).round(2),
        "val_f_r": (ltv * rng.uniform(0.5,3.0,n)).round(2), "ltv_r": ltv.round(2),
        "first_reg_dt": first_dt.strftime("%Y-%m-%d"), "last_reg_dt": last_dt.strftime("%Y-%m-%d"),
        "cum_repchs_flg": (rng.random(n) < np.clip(retention*0.8,0.1,0.9)).astype(int),
        "new_repchs_flg": rng.integers(0,2,n), "cum_prod_repchs_flg": rng.integers(0,2,n),
        "new_prod_repchs_flg": rng.integers(0,2,n), "cum_upsell_flg": rng.integers(0,2,n),
        "new_upsell_flg": rng.integers(0,2,n), "d2c_flg": rng.integers(0,2,n),
        "rr_mapping": "GUID", "age_null_yn": 0,
        "st_act_flg": (rng.random(n) < st_p).astype(int), "st_div_flg": rng.integers(0,2,n),
        "reg_diff": np.maximum((last_dt - first_dt).days, 0),
        "flag_hhp_only": rng.random(n) < 0.30, "flag_tv_only": rng.random(n) < 0.10,
        "samsungwallet_flag": rng.random(n) < wallet_p,
        "samsungwallet_first_dt": (pd.to_datetime("2021-01-01") + pd.to_timedelta(rng.integers(0,1200,n), unit="D")).strftime("%Y-%m-%d"),
        "samsunghealth_flag": rng.random(n) < health_p,
        "samsunghealth_first_dt": (pd.to_datetime("2019-01-01") + pd.to_timedelta(rng.integers(0,2000,n), unit="D")).strftime("%Y-%m-%d"),
        "smartthings_flag": rng.random(n) < st_p, "smartthings_first_dt": None,
        "premium_cnt": prem_cnt,
    })


def gen_purchase(demo: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, c in demo.iterrows():
        ap2, country = c["usr_cnty_ap2"], c["usr_cnty_name"]
        currency, fx = CURRENCIES_BY_AP2.get(ap2, ("USD",1.0))
        for _ in range(int(rng.integers(1,6))):
            cat  = rng.choice(PD_CATS, p=PD_WEIGHTS)
            pl   = PRODUCTS_BY_CAT[cat]
            nm, series, sku, pd_type, rec_type, rec_sub, smart, screen = pl[rng.integers(0,len(pl))]
            prem = int(rng.random() < 0.35)
            base = float(np.clip(rng.lognormal(5.5,0.8) if prem else rng.lognormal(4.8,0.7), 30, 3000))
            disc = base * rng.uniform(0, 0.15)
            ti   = base * rng.uniform(0,0.10) if rng.random()<0.20 else None
            rwd  = base * rng.uniform(0,0.05) if rng.random()<0.30 else None
            sale = max(base - disc - (ti or 0) - (rwd or 0), 1.0)
            odt  = pd.Timestamp("2018-01-01") + pd.Timedelta(days=int(rng.integers(0,2557)))
            stor = rng.choice(["128GB","256GB","512GB",None], p=[0.35,0.35,0.20,0.10]) if cat in ["HHP","TABLET","PC"] else None
            color= rng.choice(["BLACK","WHITE","SILVER","BLUE","CREAM"])
            rows.append({
                "index":c["index"],"purc_cnty_ap2":ap2,"purc_cnty_name":country,
                "order_id":f"{ap2[:2]}{odt.strftime('%y%m%d')}-{int(rng.integers(10_000_000,99_999_999))}",
                "order_date":odt.strftime("%Y-%m-%d"),
                "store_type":rng.choice(STORE_TYPES,p=STORE_WEIGHTS),"site_name":"Samsung.com",
                "source_app":rng.choice(["Mobile","PC"],p=[0.6,0.4]),
                "order_entries_oe_sku":sku,"order_entries_oe_name":nm,"sale_qty":1,
                "sale_amt_local":round(sale*fx,2),"price_base_local":round(base*fx,2),
                "price_discount_all_local":round(disc*fx,2),
                "price_discount_tradein_local":round(ti*fx,2) if ti else None,
                "price_discount_rewards_local":round(rwd*fx,2) if rwd else None,
                "currency":currency,"exchange_rate":fx,
                "sale_amt_usd":round(sale,2),"price_base_usd":round(base,2),
                "price_discount_all_usd":round(disc,2),
                "price_discount_tradein_usd":round(ti,2) if ti else None,
                "price_discount_rewards_usd":round(rwd,2) if rwd else None,
                "pd_division":DIV_BY_CAT[cat],"pd_group":GRP_BY_CAT[cat],"pd_category":cat,
                "pd_type":pd_type,"pd_rec_type":rec_type,"pd_rec_sub_type":rec_sub,
                "pd_series":series,"pd_name":nm,"pd_color":color,"pd_size":None,
                "pd_smart":smart,"refurbished":"N","pd_screen":screen,"pd_storage":stor,
                "pd_marketing_name":nm,"pd_description":f"{cat},{sku},{color}",
                "pd_mkt_attb01":smart,"pd_mkt_attb02":series,"pd_mkt_attb03":nm,
                "data_source":"hybris","sellin_price":round(base*0.65,2),"premium_flg":prem,
            })
    return pd.DataFrame(rows)


def gen_owned(demo: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, c in demo.iterrows():
        for idx in range(1, int(rng.integers(1,5))+1):
            cat = rng.choice(PD_CATS, p=PD_WEIGHTS)
            pl  = PRODUCTS_BY_CAT[cat]
            nm, series, sku, pd_type, rec_type, rec_sub, smart, _ = pl[rng.integers(0,len(pl))]
            reg = pd.Timestamp("2017-01-01") + pd.Timedelta(days=int(rng.integers(0,2920)))
            last_reg = reg + pd.Timedelta(days=int(rng.integers(0,300)))
            last_act = (last_reg + pd.Timedelta(days=int(rng.integers(0,90)))).strftime("%Y-%m-%d") if rng.random()<0.7 else None
            base = float(np.clip(rng.lognormal(5.0,0.8), 30, 3000))
            rows.append({
                "index":c["index"],"dvc_index":idx,
                "usr_is_last_owner":rng.choice(["Y","N"],p=[0.85,0.15]),
                "dvc_division":DIV_BY_CAT[cat],"dvc_group":GRP_BY_CAT[cat],"dvc_category":cat,
                "dvc_type":{"HHP":"Smart Phone","WEARABLE":"Wearable","TV":"TV","TABLET":"Tablet","PC":"Laptop","AUDIO":"Audio","DA":"Appliance"}[cat],
                "dvc_pd_type":pd_type,"dvc_rec_type":rec_type,"dvc_rec_sub_type":rec_sub,
                "dvc_mdl_id":sku,"dvc_mdl_nm":nm,"dvc_sku":sku,"dvc_series":series,
                "dvc_attb_color":rng.choice(["BLACK","WHITE","SILVER","BLUE","CREAM"]),
                "dvc_attb_size":None,"dvc_attb_smart":smart,"dvc_attb_etc":None,
                "dvc_acc_yn":"N","dvc_is_cellular":rng.random()<0.7,"dvc_is_wifi":True,"dvc_is_bluetooth":True,
                "dvc_is_secondhand":rng.choice(["N","Y"],p=[0.90,0.10]),
                "dvc_manufacturer":"Samsung","dvc_samsung_flag":"Y","refurbished":"N",
                "dvc_reg_date":reg.strftime("%Y-%m-%d"),"dvc_first_reg_date":reg.strftime("%Y-%m-%d"),
                "dvc_last_reg_date":last_reg.strftime("%Y-%m-%d"),"dvc_last_active_date":last_act,
                "data_source":rng.choice(["MDE","OOD"]),
                "sale_amt_usd":round(base,2),"sellin_price":round(base*0.65,2),
                "premium_flg":int(rng.random()<0.35),
            })
    return pd.DataFrame(rows)


def gen_app_usage(demo: pd.DataFrame) -> pd.DataFrame:
    rows     = []
    all_apps = SAMSUNG_APPS + NON_SAMSUNG_APPS
    base_wk  = pd.Timestamp("2025-01-06")
    for _, c in demo.iterrows():
        n_apps   = int(rng.integers(3,12))
        selected = [all_apps[i] for i in rng.choice(len(all_apps), n_apps, replace=False)]
        weeks    = int(rng.integers(2,5))
        for app_id, app_title, app_cat in selected:
            is_sam = any(app_id == a[0] for a in SAMSUNG_APPS)
            for w in range(weeks):
                ws = base_wk + pd.Timedelta(weeks=w)
                we = ws + pd.Timedelta(days=6)
                rows.append({
                    "index":c["index"],"usage_month":f"2025-W{4+w:02d}",
                    "app_id":app_id,"app_title":app_title,"app_is_samsung":is_sam,
                    "app_category":app_cat,
                    "app_game_category":rng.choice(["CASUAL","PUZZLE","STRATEGY","RPG"]) if app_cat=="GAME" else None,
                    "usage_cnt":int(rng.integers(5,120)),
                    "usage_duration_seconds":max(60,int(rng.lognormal(8,1.5) if app_cat=="GAME" else rng.lognormal(7,1.2))),
                    "fst_usage_date":ws.strftime("%Y-%m-%d"),"lst_usage_date":we.strftime("%Y-%m-%d"),
                    "dvc_cnt":1,"dvc_model_list":"['SM-S926B']",
                    "usage_month_last_day":we.strftime("%Y-%m-%d"),
                    "cii_load_dt":(we+pd.Timedelta(days=7)).strftime("%Y-%m-%d 03:00:00"),
                })
    return pd.DataFrame(rows)


def gen_interests(demo: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, c in demo.iterrows():
        active = set(rng.choice(INTERESTS, int(rng.integers(3,8)), replace=False))
        for interest in INTERESTS:
            score = float(rng.exponential(0.05) if interest in active else rng.uniform(0,0.005))
            rows.append({
                "index":c["index"],"usr_cnty_cd":CNTY_CD_BY_AP2.get(c["usr_cnty_ap2"],c["usr_cnty_ap2"]),
                "interest":interest,"category":interest.replace(" & ","_AND_").replace(" ","_"),
                "SUB_SCORE":round(score,6),"INTEREST_SCORE":round(score,6),
            })
    return pd.DataFrame(rows)


def gen_rewards(demo: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, c in demo.iterrows():
        if rng.random() > 0.60: continue
        ap2 = c["usr_cnty_ap2"]
        currency, fx = CURRENCIES_BY_AP2.get(ap2, ("USD",1.0))
        tier      = rng.choice(["Bronze","Silver","Gold","Platinum"], p=[0.40,0.30,0.20,0.10])
        tm        = {"Bronze":("T001",1),"Silver":("T002",2),"Gold":("T003",3),"Platinum":("T004",4)}
        tc, tl    = tm[tier]
        acc       = int(rng.lognormal(9,1.2))
        rdm       = int(acc * rng.uniform(0.3,0.95))
        exp       = int(acc * rng.uniform(0,0.05))
        amt       = max(0, acc-rdm-exp)
        last_acc  = pd.Timestamp("2024-01-01") + pd.Timedelta(days=int(rng.integers(0,450)))
        last_rdm  = last_acc - pd.Timedelta(days=int(rng.integers(0,90)))
        ts        = last_acc - pd.Timedelta(days=365)
        te        = last_acc + pd.Timedelta(days=365)
        rows.append({
            "index":c["index"],"rewards_cnt":1,"rewards_priority":1,
            "rwd_cnty_cd_2":CNTY_CD2_BY_AP2.get(ap2,"US"),"rwd_cnty_cd":CNTY_CD_BY_AP2.get(ap2,"USA"),
            "rwd_cnty_name":c["usr_cnty_name"],"rwd_cnty_gc":GC_BY_AP2.get(ap2,"N.America"),
            "rwd_cnty_ap2":ap2,"point_type":"Samsung Rewards",
            "point_amt":amt,"point_acc_amt":acc,"point_rdm_amt":-rdm,"point_exp_amt":exp,
            "exp_amount_1month":0,"exp_amount_3month":0,
            "last_date_acc":last_acc.strftime("%Y-%m-%d"),"last_date_rdm":last_rdm.strftime("%Y-%m-%d"),
            "tier_level_code":tc,"tier_name":tier,"tier_level":tl,
            "tier_start_date":ts.strftime("%Y-%m-%d"),"tier_end_date":te.strftime("%Y-%m-%d"),
            "best_tier_level_code":tc,"best_tier_name":tier,"best_tier_level":tl,
            "best_tier_end_date":te.strftime("%Y-%m-%d"),
            "currency":currency,"currency_rate":fx,"point_rate":0.01,
            "point_amt_usd":round(amt*0.01,2),"point_acc_amt_usd":round(acc*0.01,2),
            "point_rdm_amt_usd":round(-rdm*0.01,2),
        })
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    DATA_DIR.mkdir(exist_ok=True)
    print(f"더미 데이터 생성 중... (N={N_CUSTOMERS}명) → {DATA_DIR}")

    tables = {
        "demo":    gen_demo,
        "clv":     None,
        "purchase":None,
        "owned":   None,
        "app_usage":None,
        "interests":None,
        "rewards": None,
    }

    demo = gen_demo()
    demo.to_csv(DATA_DIR / "demo.csv", index=False)
    print(f"  demo.csv          {len(demo):>6,}행  {len(demo.columns)}컬럼")

    clv = gen_clv(demo)
    clv.to_csv(DATA_DIR / "clv.csv", index=False)
    print(f"  clv.csv           {len(clv):>6,}행  {len(clv.columns)}컬럼")

    purchase = gen_purchase(demo)
    purchase.to_csv(DATA_DIR / "purchase.csv", index=False)
    print(f"  purchase.csv      {len(purchase):>6,}행  {len(purchase.columns)}컬럼")

    owned = gen_owned(demo)
    owned.to_csv(DATA_DIR / "owned.csv", index=False)
    print(f"  owned.csv         {len(owned):>6,}행  {len(owned.columns)}컬럼")

    app_usage = gen_app_usage(demo)
    app_usage.to_csv(DATA_DIR / "app_usage.csv", index=False)
    print(f"  app_usage.csv     {len(app_usage):>6,}행  {len(app_usage.columns)}컬럼")

    interests = gen_interests(demo)
    interests.to_csv(DATA_DIR / "interests.csv", index=False)
    print(f"  interests.csv     {len(interests):>6,}행  {len(interests.columns)}컬럼")

    rewards = gen_rewards(demo)
    rewards.to_csv(DATA_DIR / "rewards.csv", index=False)
    print(f"  rewards.csv       {len(rewards):>6,}행  {len(rewards.columns)}컬럼")

    print("\n완료!")


if __name__ == "__main__":
    main()