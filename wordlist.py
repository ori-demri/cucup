from typing import Optional
from strategies.base import BaseRetailerStrategy

# ==============================================================================
# SimplyCodes Top 20 Most Issued Coupon Patterns (Empirical 54k+ Store Dataset)
# ==============================================================================
SIMPLYCODES_DATA: dict[str, list[str]] = {
    "OFF": [
        "10off", "15off", "20off", "25off", "5off", "30off", "50off", "tenoff",
        "40off", "10off50", "off20", "halfoff", "off10", "fiveoff", "15off45",
        "handoff", "35off", "15off50", "twentyoff", "coffee", "get10off", "20off25",
        "10%off", "take10off", "kickoff", "20off75", "15off35", "20off49", "25off75",
        "off15", "10offtoday", "15off49", "15off25", "specialoffers", "20off35",
        "15off40", "20%off", "dayoff", "15%off", "get20off", "20off100", "off5",
        "60off", "10offnow", "15offnow"
    ],
    "SAVE": [
        "save10", "save20", "save15", "save25", "save30", "save5", "save50", "save40",
        "save", "savemore", "savebig", "savenow", "save35", "save100", "save10now",
        "save60", "save12", "saveten", "save5now", "save75", "save20now", "summersave",
        "65save", "save15now", "save3", "save200", "20save", "save45", "savefive",
        "save150", "save25now", "10save", "save8", "save70", "save2019", "save7",
        "25save", "springsave", "savetoday", "savebig25", "saveme10", "savegreen",
        "save18", "save65", "savemore20"
    ],
    "WELCOME": [
        "welcome10", "welcome", "welcome15", "welcome20", "welcome5", "welcome25",
        "welcomeback", "welcome30", "welcome19", "welcome50", "welcome2020", "welcome18",
        "welcome2019", "welcomeback10", "welcome16", "welcome2018", "welcome17",
        "welcome40", "10welcome", "welcomeback15", "welcome35", "welcomehome",
        "welcomeback20", "welcome10off", "welcomegift", "welcome2", "welcome2017",
        "welcome15off", "welcome413", "welcomefall", "welcome3", "welcome1o",
        "welcome400", "15welcome", "welcome361", "welcome-10", "welcome6", "welcome12",
        "welcome100", "20welcome", "welcome10%", "welcome05", "welcomev3ffnsmk", "welcome374"
    ],
    "FREE": [
        "freeship", "freeshipping", "shipfree", "freedom", "free", "shipsfree", "freegift",
        "freeship49", "ship4free", "freeship50", "freeship29", "freebie", "freedom20",
        "freedel", "free10", "freeship19", "free20", "freeship75", "free50", "freeship20",
        "freedelivery", "free15", "freeship100", "freedom15", "free2day", "shipitfree",
        "freeship25", "freeship18", "freetee", "freeship30", "bogofree", "freedom25",
        "free25", "freedom10", "freemask", "freebag", "free30", "freeship17",
        "freeship2020", "freedom30", "4free", "freesocks", "50free", "2free"
    ],
    "NEW": [
        "newyear", "new10", "new15", "new20", "new", "newyear20", "new25", "new5",
        "new30", "newyou", "newsletter", "newyear10", "newyear15", "newsletter10",
        "new2020", "newyear2020", "news10", "newbie", "newyear25", "newsite",
        "newyear18", "newyear30", "new50", "newyear19", "happynewyear", "newcustomer",
        "newlook", "new19", "newnew", "new40", "newyears", "new2019", "new18",
        "newsletter15", "new8", "newfriend", "new2018", "newyear2019", "renew",
        "news15", "new12", "newyear2018", "newbie10", "newyear40", "20new"
    ],
    "SHIP": [
        "freeship", "freeshipping", "shipfree", "shipsfree", "24ship", "29ship", "34ship",
        "freeship49", "ship4free", "39ship", "ship29", "19ship", "freeship50", "freeship29",
        "ship50", "ship", "30ship", "shipit", "ship24", "49ship", "freeship19", "44ship",
        "shipnow", "freeship75", "freeship20", "99ship", "freeship100", "shipping",
        "ship75", "shipitfree", "freeship25", "freeship18", "shipme", "79ship",
        "freeship30", "springship", "summership", "ship25", "ship2me", "ship49",
        "freeship17", "ship19", "freeship2020", "25ship"
    ],
    "SUMMER": [
        "summer", "summer20", "summer15", "summer10", "summer25", "summer30", "summersale",
        "summer19", "summer50", "summer40", "summer18", "summerfun", "summer2020",
        "byesummer", "summertime", "summer17", "endofsummer", "summer2019", "summer5",
        "summerlove", "hellosummer", "summer35", "summersave", "summer2018", "midsummer",
        "summership", "summerend", "summervibes", "summersavings", "summer60", "hotsummer",
        "summer2017", "summerskin", "summersun", "summer12", "summer100", "summerlovin",
        "summerflash", "summersale20", "20summer", "endlesssummer", "summerbogo",
        "summerdays", "summerstyle", "summerheat"
    ],
    "LOVE": [
        "love", "love20", "love15", "love10", "love25", "lovemom", "love30", "summerlove",
        "love2020", "love50", "love14", "love40", "lovedad", "selflove", "clover",
        "love18", "loveit", "momlove", "loveyou", "weloveyou", "ilovemom", "lovely",
        "fallinlove", "love5", "love19", "lovefall", "love2018", "withlove", "love35",
        "sharethelove", "lovemom20", "lovemum", "laboroflove", "spreadlove", "loveyoumom",
        "loveme", "mamalove", "love2019", "loveu", "welovemom", "20love", "15love",
        "truelove", "puppylove", "loveya"
    ],
    "BF": [
        "bf20", "bf2019", "bf30", "bf25", "bf15", "bfcm", "bf10", "bf40",
        "bf2018", "bf19", "bf50", "bf2017", "bfcm19", "bfcm2019", "bfcm20", "bfcm30",
        "bf18", "bf35", "bfcm25", "bff", "bfsale", "bfj", "bfriday", "bf5", "bfcm15",
        "earlybf", "bfcm18", "bf17", "bfcm40", "prebf", "bf", "bff20", "bfcm2018",
        "bfcm10", "bf100", "bfcm50", "febflash", "bfvip", "bf60", "nhlbf19", "bf12",
        "bf45", "tgibf", "bf200", "bff15"
    ],
    "SPRING": [
        "spring", "spring20", "spring15", "spring10", "spring25", "spring30", "springsale",
        "spring19", "spring2020", "spring18", "spring40", "spring50", "springtime",
        "springclean", "hellospring", "spring5", "springfling", "spring2019", "spring2018",
        "springbreak", "spring17", "springcleaning", "springfever", "spring35", "springship",
        "springforward", "hispring", "springsavings", "20spring", "spring60", "springsave",
        "spring100", "springishere", "sspspring19", "happyspring", "springsale20",
        "springdeal", "spring12", "spring2017", "springbogo", "spring75", "15spring",
        "springfree", "spring16", "spring2"
    ],
    "JULY": [
        "july4", "july4th", "july20", "july", "july25", "july15", "july10", "july30",
        "july40", "4july", "4thofjuly", "july50", "july2020", "july19", "4thjuly",
        "julysale", "july18", "july2019", "july5", "xmasjuly", "jul20", "julia10",
        "july17", "julyxmas", "xmasinjuly", "julia", "july35", "julyfourth", "july4sale",
        "july2018", "4july20", "julia20", "julia15", "july420", "christmasinjuly",
        "julie10", "byejuly", "july419", "july60", "jul10", "julyship", "july100",
        "julysave", "julybogo", "4july25", "4july19", "julyfree", "julyfun", "july12",
        "july42020", "4july18", "15july"
    ],
    "FALL": [
        "fall20", "fall", "fall15", "fall25", "fall10", "fall30", "fall19", "fall2019",
        "fallsale", "fall50", "hellofall", "fall40", "fallflash", "fall2020", "fall18",
        "30fall", "fall17", "fall2018", "fall5", "fallfun", "fall2017", "fallsavings",
        "fall35", "fallback", "happyfall", "fallinlove", "lovefall", "fallship", "fallbogo",
        "fallfaves", "fallyall", "fall12", "20fall", "fallsave", "fallishere", "fall100",
        "freefall", "15fall", "fall60", "fallvibes", "fall75", "fallstyle", "newfall",
        "fallready", "fall2015"
    ],
    "FLASH": [
        "flash", "flash20", "flash25", "flash30", "flash15", "flashsale", "flash10", "flash40",
        "flash50", "fallflash", "flash35", "15flash25", "20flash25", "flashback", "flash5",
        "flash19", "flashsale20", "30flash", "flash60", "flashfriday", "flashy",
        "summerflash", "flash2020", "flash18", "20flash", "flash24", "flash48", "flash12",
        "flash45", "flash17", "febflash", "25flash", "flashsale30", "flashsale15",
        "flash100", "40flash", "flashsale25", "flashsale10", "juneflash", "mayflash",
        "flash70", "flash4", "flash22"
    ],
    "GET": [
        "get10", "get20", "get15", "get25", "get30", "get5", "together", "get50",
        "buy2get1", "get10off", "get40", "get10now", "getaway", "getmore", "get20off",
        "buy1get1", "getcozy", "getlucky", "get5off", "get5now", "get15off", "getready",
        "get35", "bettertogether", "getit", "getstarted", "get15now", "get3", "buy3get1",
        "together20", "getfit", "get25off", "get60", "get2", "get20now", "together25",
        "get30off", "neverforget", "get1free", "get100", "getitnow", "getoutside",
        "together15", "getset"
    ],
    "GIFT": [
        "gift", "gift20", "gift10", "gift15", "gift25", "freegift", "gift30", "gifts",
        "gift50", "gift40", "gift4u", "gift5", "gift19", "giftnow", "gifts20", "giftme",
        "gifted", "mygift", "gifting", "gift100", "gift18", "gift4you", "gift65",
        "holidaygift", "giftcard", "yourgift", "gift35", "newgifts", "gift3", "gift2019",
        "bestgift", "savegifts", "xmasgift", "nflgift", "giftnfl29", "giftcard20",
        "summergift", "gift4mom", "saveongifts", "giftnfl36", "2019gift", "gift17",
        "welcomegift", "gifts25", "gift1"
    ],
    "MOM": [
        "mom", "mom20", "mom15", "lovemom", "mom25", "mom10", "mom30", "momsday",
        "formom", "mom2020", "thanksmom", "mom19", "mom18", "mom2019", "momday",
        "momlove", "mom50", "mom2018", "ilovemom", "bestmom", "mom40", "mom17",
        "supermom", "mom2017", "moms", "4mom", "lovemom20", "loveyoumom", "mommy",
        "luvmom", "treatmom", "welovemom", "mom5", "mom35", "momsrule", "momsrock",
        "gift4mom", "happymom", "momlife", "moms20", "momsday20", "momday20", "dogmom",
        "momrocks", "loveumom"
    ],
    "FREESHIP": [
        "freeship", "freeshipping", "freeship49", "freeship50", "freeship29", "freeship19",
        "freeship75", "freeship20", "freeship100", "freeship25", "freeship18", "freeship30",
        "freeship17", "freeship2020", "freeship35", "freeship99", "freeship10", "freeship15",
        "freeshipday", "freeship40", "freeship150", "freeship2019", "freeshipnow",
        "freeship24", "freeshipusa", "freeship1", "freeship4u", "freeshipfriday",
        "freeshipus", "freeship2", "freeshipp", "freeshipping19", "freeshipjuly",
        "usfreeship", "freeship60", "freeshiping", "fallfreeship", "freeshipping50",
        "honeyfreeship", "freeship2018", "freeshipweekend", "freeship45", "freeship5",
        "freeship200", "freeship2017"
    ],
    "CYBER": [
        "cyber", "cybermonday", "cyber20", "cyber30", "cyber25", "cyber19", "cyber10",
        "cyber15", "cyber40", "cyber50", "cyber18", "cyber2019", "cyberweek", "cyber35",
        "cyber17", "cybersale", "cyber2018", "cybermon", "cyber2017", "cybermonday19",
        "cyber5", "cyber60", "cybermonday20", "cyber16", "cybermonday2019", "cybermonday30",
        "cyber100", "cyberdeal", "cybersave", "cybermonday18", "cybermonday25", "cyber2",
        "cybermonday15", "cyber45", "cyber75", "cybership", "cybermonday10", "30cyber",
        "cyberweek19", "cyber12", "cyberbogo", "cyberwow", "cyber1", "cybermonday17",
        "cybermonday2018"
    ],
    "BLACK": [
        "blackfriday", "black", "black20", "black25", "black30", "blackfriday19",
        "blackfriday20", "black15", "black10", "blackfriday25", "blackfriday2019",
        "blackfriday30", "blackout", "black40", "black50", "blackfriday18", "black19",
        "blackfriday15", "blackfriday40", "blackfriday2018", "blackfriday10", "blackfri",
        "blackfriday50", "black18", "blackfriday17", "blackfriyay", "black35", "black2019",
        "blackfriday2017", "black17", "black5", "black2018", "preblackfriday",
        "blackfriday35", "blackcat", "black60", "preblack", "blackfri19", "blackfri20",
        "black12", "black2017", "blackfri25", "black100", "blackfridayvip"
    ]
}


class WordlistEngine:
    """
    Domain, statistical dataset, and brand-aware coupon candidate generator.
    Organized by hierarchical empirical probability tiers with strict deduplication.
    """

    @staticmethod
    def generate_candidates(
        strategy: Optional[BaseRetailerStrategy] = None,
        brand_tokens: Optional[list[str]] = None,
        brand_tokens_he: Optional[list[str]] = None,
        niche_keywords: Optional[list[str]] = None,
        include_leetspeak: bool = False,
        custom_seeds: Optional[list[str]] = None,
    ) -> list[str]:
        if strategy:
            strat_en, strat_he = strategy.get_brand_tokens()
            brands = [b.lower() for b in (brand_tokens or strat_en)]
            brands_he = brand_tokens_he or strat_he
            strat_seeds = strategy.get_dedicated_seeds()
            strat_niche = strategy.get_niche_keywords()
        else:
            brands = [b.lower() for b in (brand_tokens or ["talron", "tal-ron", "tal", "ron"])]
            brands_he = brand_tokens_he or ["טלרון", "טל-רון", "טל", "רון"]
            strat_seeds = [
                "new30", "welcome5", "sale10", "sale20", "sale30", "sale40", "sale50",
                "talron50", "welcome10", "talron10",
                "tal1", "ron10", "tal10", "ron1", "tal5", "ron5",
            ]
            strat_niche = []

        niche_tokens = niche_keywords or strat_niche

        # Standard discount numbers and year representations
        discount_nums = [10, 15, 20, 5, 25, 30, 35, 40, 50, 60, 70, 75, 80, 100]
        core_nums = [10, 15, 20, 5, 25, 30, 40, 50]
        years_short = ["24", "25", "26"]
        years_full = ["2024", "2025", "2026"]
        all_years = years_short + years_full
        modern_years = ["24", "25", "26", "2024", "2025", "2026"]
        seasons = ["spring", "summer", "fall", "autumn", "winter"]

        raw_candidates: list[str] = []

        # ======================================================================
        # 0. Custom Seeds & Strategy Dedicated High-Probability Seeds
        # ======================================================================
        if custom_seeds:
            raw_candidates.extend(custom_seeds)
        raw_candidates.extend(strat_seeds)

        # ======================================================================
        # 1. SimplyCodes #1: OFF Vector (54.3k stores, User's Highest Priority)
        # ======================================================================
        for n in discount_nums:
            raw_candidates.append(f"{n}off")
            raw_candidates.append(f"{n}-off")
            raw_candidates.append(f"{n}_off")
        raw_candidates.extend(SIMPLYCODES_DATA["OFF"])
        raw_candidates.append("off")

        # ======================================================================
        # 2. TEST & Dev / Staging Vectors (Common dev leftovers)
        # ======================================================================
        raw_candidates.append("test")
        for n in [1, 5, 10, 15, 20, 25, 30, 50, 100]:
            raw_candidates.append(f"test{n}")
            raw_candidates.append(f"test-{n}")
        for dev_word in ["dev", "qa", "stage", "staging", "demo", "admintest", "testcoupon"]:
            raw_candidates.append(dev_word)

        # ======================================================================
        # 3. SimplyCodes #2: SAVE Vector (42.1k stores)
        # ======================================================================
        raw_candidates.append("save")
        for n in discount_nums:
            raw_candidates.append(f"save{n}")
            raw_candidates.append(f"save-{n}")
        raw_candidates.extend(SIMPLYCODES_DATA["SAVE"])

        # ======================================================================
        # 4. SimplyCodes #3: WELCOME Vector (41.5k stores)
        # ======================================================================
        raw_candidates.append("welcome")
        for n in discount_nums:
            raw_candidates.append(f"welcome{n}")
            raw_candidates.append(f"welcome-{n}")
        raw_candidates.extend(SIMPLYCODES_DATA["WELCOME"])
        for y in modern_years:
            raw_candidates.append(f"welcome{y}")
            raw_candidates.append(f"welcome-{y}")

        # ======================================================================
        # 5. SimplyCodes #4, #6, #18: FREE / SHIP / FREESHIP (Combined 70k+ stores)
        # ======================================================================
        raw_candidates.extend(SIMPLYCODES_DATA["FREE"])
        raw_candidates.extend(SIMPLYCODES_DATA["SHIP"])
        raw_candidates.extend(SIMPLYCODES_DATA["FREESHIP"])
        for y in modern_years:
            raw_candidates.append(f"freeship{y}")
            raw_candidates.append(f"shipfree{y}")
        raw_candidates.extend(["משלוחחינם", "משלוח-חינם", "משלוח_חינם"])

        # ======================================================================
        # 6. SimplyCodes #5: NEW Vector (29.5k stores)
        # ======================================================================
        raw_candidates.append("new")
        for n in discount_nums:
            raw_candidates.append(f"new{n}")
            raw_candidates.append(f"new-{n}")
        raw_candidates.extend(SIMPLYCODES_DATA["NEW"])
        for y in modern_years:
            raw_candidates.append(f"new{y}")
            raw_candidates.append(f"newyear{y}")

        # ======================================================================
        # 7. ADMIN, EMPLOYEE, MILITARY (Internal / privileged codes)
        # ======================================================================
        for role in ["admin", "employee", "military", "staff", "team", "internal", "corp"]:
            raw_candidates.append(role)
            for n in [10, 15, 20, 25, 30, 40, 50, 5, 100]:
                raw_candidates.append(f"{role}{n}")
                raw_candidates.append(f"{role}-{n}")

        # ======================================================================
        # 8. SALE{num} Vector (English & Hebrew)
        # ======================================================================
        raw_candidates.append("sale")
        for n in discount_nums:
            raw_candidates.append(f"sale{n}")
            raw_candidates.append(f"sale-{n}")
            raw_candidates.append(f"sale_{n}")
        for n in discount_nums:
            raw_candidates.append(f"סייל{n}")
            raw_candidates.append(f"סייל-{n}")

        # ======================================================================
        # 9. SimplyCodes #7: SUMMER Vector (26.3k stores)
        # ======================================================================
        raw_candidates.append("summer")
        for n in core_nums:
            raw_candidates.append(f"summer{n}")
            raw_candidates.append(f"summer-{n}")
        raw_candidates.extend(SIMPLYCODES_DATA["SUMMER"])
        for y in modern_years:
            raw_candidates.append(f"summer{y}")
            raw_candidates.append(f"summer-{y}")

        # ======================================================================
        # 10. SimplyCodes #8 & #17: LOVE & MOM Vectors (34k+ stores)
        # ======================================================================
        raw_candidates.append("love")
        for n in core_nums:
            raw_candidates.append(f"love{n}")
            raw_candidates.append(f"love-{n}")
        raw_candidates.extend(SIMPLYCODES_DATA["LOVE"])
        raw_candidates.append("mom")
        for n in core_nums:
            raw_candidates.append(f"mom{n}")
            raw_candidates.append(f"mom-{n}")
        raw_candidates.extend(SIMPLYCODES_DATA["MOM"])
        for y in modern_years:
            raw_candidates.append(f"love{y}")
            raw_candidates.append(f"mom{y}")

        # ======================================================================
        # 11. SimplyCodes #9 & #20: BF & BLACK Vectors (31k+ stores)
        # ======================================================================
        raw_candidates.extend(["bf", "blackfriday", "black", "bfcm"])
        for n in core_nums:
            raw_candidates.append(f"bf{n}")
            raw_candidates.append(f"black{n}")
            raw_candidates.append(f"blackfriday{n}")
        raw_candidates.extend(SIMPLYCODES_DATA["BF"])
        raw_candidates.extend(SIMPLYCODES_DATA["BLACK"])
        for y in modern_years:
            raw_candidates.append(f"bf{y}")
            raw_candidates.append(f"bfcm{y}")
            raw_candidates.append(f"blackfriday{y}")

        # ======================================================================
        # 12. SimplyCodes #10: SPRING Vector (17.9k stores)
        # ======================================================================
        raw_candidates.append("spring")
        for n in core_nums:
            raw_candidates.append(f"spring{n}")
            raw_candidates.append(f"spring-{n}")
        raw_candidates.extend(SIMPLYCODES_DATA["SPRING"])
        for y in modern_years:
            raw_candidates.append(f"spring{y}")
            raw_candidates.append(f"spring-{y}")

        # ======================================================================
        # 13. SimplyCodes #11 & #14: JULY & Independence Day Vectors (17.3k stores)
        # ======================================================================
        raw_candidates.append("july")
        for n in core_nums:
            raw_candidates.append(f"july{n}")
        raw_candidates.extend(SIMPLYCODES_DATA["JULY"])
        for y in modern_years:
            raw_candidates.append(f"july{y}")
            raw_candidates.append(f"4july{y}")
            raw_candidates.append(f"july4{y}")

        # ======================================================================
        # 14. SimplyCodes #12: FALL & Autumn Vectors (16.7k stores)
        # ======================================================================
        for fkw in ["fall", "autumn"]:
            raw_candidates.append(fkw)
            for n in core_nums:
                raw_candidates.append(f"{fkw}{n}")
                raw_candidates.append(f"{fkw}-{n}")
            for y in modern_years:
                raw_candidates.append(f"{fkw}{y}")
        raw_candidates.extend(SIMPLYCODES_DATA["FALL"])

        # ======================================================================
        # 15. SimplyCodes #13: FLASH Vectors (14.1k stores)
        # ======================================================================
        raw_candidates.append("flash")
        for n in core_nums:
            raw_candidates.append(f"flash{n}")
            raw_candidates.append(f"flash-{n}")
        raw_candidates.extend(SIMPLYCODES_DATA["FLASH"])

        # ======================================================================
        # 16. SimplyCodes #15: GET Vectors (13.1k stores)
        # ======================================================================
        for n in discount_nums:
            raw_candidates.append(f"get{n}")
            raw_candidates.append(f"get-{n}")
        raw_candidates.extend(SIMPLYCODES_DATA["GET"])

        # ======================================================================
        # 17. SimplyCodes #16: GIFT Vectors (12.7k stores)
        # ======================================================================
        raw_candidates.append("gift")
        for n in discount_nums:
            raw_candidates.append(f"gift{n}")
            raw_candidates.append(f"gift-{n}")
        raw_candidates.extend(SIMPLYCODES_DATA["GIFT"])

        # ======================================================================
        # 18. SimplyCodes #19: CYBER Vectors (11.7k stores)
        # ======================================================================
        raw_candidates.extend(["cyber", "cybermonday", "cyberweek"])
        for n in core_nums:
            raw_candidates.append(f"cyber{n}")
            raw_candidates.append(f"cybermonday{n}")
        raw_candidates.extend(SIMPLYCODES_DATA["CYBER"])
        for y in modern_years:
            raw_candidates.append(f"cyber{y}")
            raw_candidates.append(f"cybermonday{y}")

        # ======================================================================
        # 19. Other Seasons & Cart Incentives (Winter, Deal, Sorry, Affiliate)
        # ======================================================================
        raw_candidates.append("winter")
        for n in core_nums:
            raw_candidates.append(f"winter{n}")
            raw_candidates.append(f"winter-{n}")
        for y in all_years:
            raw_candidates.append(f"winter{y}")

        for kw in ["deal", "deals", "sorry", "apology", "affiliate", "ambassador", "thankyou", "thanks", "stock", "welcomeback"]:
            raw_candidates.append(kw)
            for n in core_nums:
                raw_candidates.append(f"{kw}{n}")
                raw_candidates.append(f"{kw}-{n}")

        # ======================================================================
        # 20. USA & Popular Global Holidays (Turkey, Love, Valentine, etc.)
        # ======================================================================
        us_holidays = [
            "turkey", "thanksgiving", "thanks", "giving",
            "valentine", "valentines", "cupid", "hearts", "bemyvalentine", "xoxo",
            "holiday", "holidays", "christmas", "xmas", "halloween", "spooky",
            "health", "mobile", "app"
        ]
        for h in us_holidays:
            raw_candidates.append(h)
            for n in core_nums:
                raw_candidates.append(f"{h}{n}")
                raw_candidates.append(f"{h}-{n}")
            for y in all_years:
                raw_candidates.append(f"{h}{y}")

        # ======================================================================
        # 21. Jewish & Israeli Holidays (Transliterations & Hebrew)
        # ======================================================================
        jewish_holidays_en = [
            "passover", "pesach", "pesakh", "purim", "roshhashana", "roshhashanah",
            "shanatova", "sukkot", "succot", "hanukkah", "chanukah", "shavuot",
            "shabbat", "shabbos", "tubav", "tu-bav", "tubeav", "twobeav", "tu-beav",
            "mimouna", "chagsameach", "hagsameach"
        ]
        for jh in jewish_holidays_en:
            raw_candidates.append(jh)
            for n in core_nums:
                raw_candidates.append(f"{jh}{n}")
                raw_candidates.append(f"{jh}-{n}")
            for y in all_years:
                raw_candidates.append(f"{jh}{y}")

        jewish_holidays_he = [
            "פסח", "חגפסח", "פורים", "חגפורים", "עדלאידע", "ראשהשנה", "שנהטובה",
            "סוכות", "חגסוכות", "חנוכה", "חגחנוכה", "שבועות", "שבת", "שבתשלום",
            "סופש", "טובאב", "טו-באב", "אהבה", "חגשמח"
        ]
        for jhe in jewish_holidays_he:
            raw_candidates.append(jhe)
            for n in core_nums:
                raw_candidates.append(f"{jhe}{n}")
                raw_candidates.append(f"{jhe}-{n}")
            for y in all_years:
                raw_candidates.append(f"{jhe}{y}")

        # ======================================================================
        # 22. Hebrew Greetings, Club & Discount Keywords
        # ======================================================================
        hebrew_unicode = [
            "ברוכים הבאים", "ברוכיםהבאים", "מועדון", "הנחה", "הנחה5", "הנחה10",
            "הנחה15", "הנחה20", "הנחה25", "הנחה30", "הנחה40", "הנחה50", "הנחה100", "מתנה",
            "מבצע", "מבצע10", "מבצע20", "מבצע30", "מבצע40", "מבצע50",
            "סייל", "סייל10", "סייל20", "סייל30", "סייל40", "סייל50", "סייל70",
            "קופון", "קופון10", "קופון20", "קופון30", "קופון40", "קופון50",
            "שבת שלום", "חבר מביא חבר"
        ]
        raw_candidates.extend(hebrew_unicode)

        # ======================================================================
        # 23. Target Brand Permutations (English & Hebrew)
        # ======================================================================
        for b in brands:
            raw_candidates.append(b)
            for num in discount_nums:
                raw_candidates.append(f"{b}{num}")
                raw_candidates.append(f"{b}-{num}")
                raw_candidates.append(f"{b}_{num}")
            for y in all_years:
                raw_candidates.append(f"{b}{y}")
            for suf in ["vip", "club", "sale", "save", "off", "gift"]:
                raw_candidates.append(f"{b}{suf}")
                raw_candidates.append(f"{b}_{suf}")

        for hb in brands_he:
            raw_candidates.append(hb)
            for num in discount_nums:
                raw_candidates.append(f"{hb}{num}")
                raw_candidates.append(f"{hb}-{num}")
                raw_candidates.append(f"{hb}_{num}")
            for y in all_years:
                raw_candidates.append(f"{hb}{y}")
            for suf in ["מועדון", "הנחה", "ויאיפי", "מתנה", "סייל"]:
                raw_candidates.append(f"{hb}{suf}")
                raw_candidates.append(f"{hb}_{suf}")

        # ======================================================================
        # 24. Industry / Retailer Niche Vectors
        # ======================================================================
        for n in niche_tokens:
            raw_candidates.append(n)
            for p in core_nums:
                raw_candidates.append(f"{n}{p}")
                raw_candidates.append(f"{n}-{p}")
            for y in all_years:
                raw_candidates.append(f"{n}{y}")
                raw_candidates.append(f"{n}-{y}")

        # ======================================================================
        # 25. Standard E-Commerce Discount Affixes
        # ======================================================================
        for p in discount_nums:
            raw_candidates.append(f"discount{p}")
            raw_candidates.append(f"{p}discount")
            raw_candidates.append(f"{p}percent")
            raw_candidates.append(f"{p}ils")
            raw_candidates.append(f"{p}nis")

        # ======================================================================
        # 26. Israeli Cities & Regional Geographic Identity (Hebrew & English)
        # ======================================================================
        israeli_cities_en = [
            "tlv", "telaviv", "jerusalem", "jlm", "haifa", "rishon", "rishonlezion",
            "ashdod", "petahtikva", "pt", "netanya", "beersheva", "beersheba",
            "holon", "bneibrak", "ramatgan", "rg", "rehovot", "batyam", "ashkelon",
            "herzliya", "kfarsaba", "hadera", "modiin", "raanana", "givataim",
            "eilat", "tiberias", "akko", "karmiel", "krayot", "sharon", "tzafon",
            "darom", "merkaz", "gushdan"
        ]

        israeli_cities_he = [
            "תלאביב", "תל-אביב", "ירושלים", "חיפה", "ראשון", "ראשוןלציון",
            "אשדוד", "פתחתקווה", "פתח-תקווה", "נתניה", "בארשבע", "באר-שבע",
            "חולון", "בניברק", "רמתגן", "רמת-גן", "רחובות", "בתים", "בת-ים",
            "אשקלון", "הרצליה", "כפרסבא", "כפר-סבא", "חדרה", "מודיעין",
            "רעננה", "גבעתיים", "אילת", "טבריה", "עכו", "כרמיאל", "קריות",
            "שרון", "צפון", "דרום", "מרכז", "גושדן"
        ]

        geo_numbers = [10, 15, 20, 25, 30, 5, 50, 100]

        for city in israeli_cities_en + israeli_cities_he:
            raw_candidates.append(city)
            for n in geo_numbers:
                raw_candidates.append(f"{city}{n}")       # Suffix (tlv10, תלאביב10)
                raw_candidates.append(f"{n}{city}")       # Prefix (10tlv, 10תלאביב)
                raw_candidates.append(f"{city}-{n}")
                raw_candidates.append(f"{n}-{city}")
            for y in modern_years:
                raw_candidates.append(f"{city}{y}")       # tlv24, tlv2024
                raw_candidates.append(f"{y}{city}")       # 24tlv, 2024tlv
            for suf in ["free", "vip", "club", "sale", "delivery"]:
                raw_candidates.append(f"{city}{suf}")

        # ======================================================================
        # 27. Popular Israeli First Names & Nicknames (Hebrew & English)
        # ======================================================================
        first_names_en = [
            # Classic & Popular
            "tal", "ron", "dana", "noa", "adi", "yael", "maya", "shir", "tom",
            "tomer", "omer", "guy", "mor", "bar", "dan", "dani", "roei", "yuval",
            "eden", "sapir", "amit", "shani", "ortal", "lior", "aviv", "itay",
            "daniel", "ori", "shira", "hadar", "rotem", "ido", "alon", "matan",
            "tamar", "yonatan", "yoni", "yoav", "eli", "sharon", "michal", "hila",
            "liron", "or", "shahar", "gal", "niv", "ran", "gilad", "gil", "ben",
            "noam", "eitan", "eyal", "dor", "ofir", "liam", "shai", "inbar", "raz",
            "nadav", "yarden", "avigail", "chen", "keren", "inbal", "moran", "ella",
            "lia", "may", "lee", "ariel", "ronen", "yossi", "asaf", "ilan",
            # Nicknames & Extended Demographic Names
            "moti", "avi", "kobi", "dudu", "itzik", "tzvika", "chaim", "moshe",
            "yaakov", "david", "yosef", "doron", "ohad", "roy", "benni", "beni",
            "gadi", "shlomi", "nitsan", "nitzan", "agam", "romi", "mia", "talia",
            "alma", "gaya", "ofri", "libi", "arbel", "yaara", "einav", "anna",
            "neta", "danit", "coral", "avivit", "linor", "katya"
        ]

        first_names_he = [
            # שמות קלאסיים ופופולריים
            "טל", "רון", "דנה", "נועה", "נוע", "עדי", "יעל", "מאיה", "מיה", "שיר",
            "תום", "תומר", "עומר", "גיא", "מור", "בר", "דן", "דני", "רועי", "יובל",
            "עדן", "ספיר", "עמית", "שני", "אורטל", "ליאור", "אביב", "איתי", "דניאל",
            "אורי", "שירה", "הדר", "רותם", "עידו", "אלון", "מתן", "תמר", "יונתן",
            "יוני", "יואב", "אלי", "שרון", "מיכל", "הילה", "לירון", "אור", "שחר",
            "גל", "ניב", "רן", "גלעד", "גיל", "בן", "נועם", "איתן", "אייל", "דור",
            "אופיר", "ליאם", "שי", "ענבר", "רז", "נדב", "ירדן", "אביגיל", "חן",
            "קרן", "ענבל", "מורן", "אלה", "ליה", "מאי", "לי", "אריאל", "רונן",
            "יוסי", "אסף", "אילן",
            # כינויים ושמות נפוצים נוספים
            "מוטי", "אבי", "קובי", "דודו", "איציק", "צביקה", "חיים", "משה", "יעקב",
            "דוד", "יוסף", "דורון", "אוהד", "רועי", "בני", "גדי", "שלומי", "ניצן",
            "אגם", "רומי", "טליה", "עלמה", "גאיה", "עופרי", "ליבי", "ארבל", "יערה",
            "עינב", "אנה", "נטע", "דנית", "קורל", "אביבית", "לינור", "קטי"
        ]

        name_numbers = [10, 15, 20, 5, 25, 30, 50, 1, 2, 3, 7, 12, 100]

        for name in first_names_en + first_names_he:
            raw_candidates.append(name)
            # Both Suffix AND Prefix Number Permutations!
            for n in name_numbers:
                raw_candidates.append(f"{name}{n}")       # maya10, מאיה10
                raw_candidates.append(f"{n}{name}")       # 10maya, 10מאיה
            for n in [5, 10, 15, 20, 25, 50]:
                raw_candidates.append(f"{name}-{n}")      # maya-10
                raw_candidates.append(f"{n}-{name}")      # 10-maya
                raw_candidates.append(f"{name}_{n}")      # maya_10
            for y in modern_years:
                raw_candidates.append(f"{name}{y}")       # maya2024, maya24
                raw_candidates.append(f"{y}{name}")       # 2024maya, 24maya
            for suf in ["vip", "love", "gift"]:
                raw_candidates.append(f"{name}{suf}")     # mayavip

        # ======================================================================
        # 28. Common Israeli Family Names (Hebrew & English) alongside Numbers
        # ======================================================================
        family_names_en = [
            "cohen", "kohen", "levi", "levy", "mizrahi", "mizrachi", "peretz",
            "biton", "bitton", "dahan", "avraham", "abraham", "friedman", "malka",
            "azulay", "azoulay", "katz", "yosef", "joseph", "david", "amar",
            "hadad", "ohayon", "gabay", "gabbay", "shalom", "lavi", "ashkenazi",
            "rubin", "klein", "shapira", "elbaz", "vaknin", "berkovich", "berkowitz",
            "golan", "sasson", "hazan", "schwartz", "shwartz", "segal", "maman",
            "stern", "goldstein", "hershkovitz", "hershkowitz", "levin", "suissa",
            "suisa", "ovadia", "tzur", "zur", "shlomo", "sarfati", "yaakov", "katzir",
            "dayan", "barkat", "navon", "peled", "ron"
        ]

        family_names_he = [
            "כהן", "לוי", "מזרחי", "פרץ", "ביטון", "דהן", "אברהם", "פרידמן",
            "מלכה", "אזולאי", "כץ", "יוסף", "דוד", "עמר", "חדד", "אוחיון",
            "גבאי", "שלום", "לביא", "אשכנזי", "רובין", "קליין", "שפירא", "אלבז",
            "ועקנין", "וקנין", "ברקוביץ", "ברקוביץ'", "גולן", "ששון", "חזן",
            "שוורץ", "סגל", "ממן", "שטרן", "גולדשטיין", "הרשקוביץ", "לוין",
            "סוויסה", "סויסה", "עובדיה", "צור", "שלמה", "צרפתי", "יעקב", "קציר",
            "דיין", "ברקת", "נבון", "פלד", "רון"
        ]

        for fam in family_names_en + family_names_he:
            raw_candidates.append(fam)
            for n in [10, 15, 20, 5, 25, 30, 50]:
                raw_candidates.append(f"{fam}{n}")       # cohen10, כהן10
                raw_candidates.append(f"{n}{fam}")       # 10cohen, 10כהן
                raw_candidates.append(f"{fam}-{n}")
                raw_candidates.append(f"{n}-{fam}")

        # ======================================================================
        # 29. Senior Behavioral Psychologist: SMB Cognitive Biases & Cultural Heuristics
        # ======================================================================
        # Cognitive Bias 1: Nepotism & Family Circle Heuristic ("Love for the tribe")
        family_circle_en = [
            "family", "mishpaha", "imma", "abba", "saba", "savta", "dod", "doda",
            "ahot", "ah", "yeladim", "kids", "baby", "buba"
        ]
        family_circle_he = [
            "משפחה", "אמא", "אבא", "סבא", "סבתא", "דוד", "דודה", "אחות", "אח",
            "ילדים", "בייבי", "תינוק", "בובה"
        ]

        # Cognitive Bias 2: Kombina & Transactional Favoritism ("The Insider Deal")
        kombina_slang_en = [
            "kombina", "protekzia", "haver", "haverim", "achla", "sababa", "boss",
            "pinuk", "matana", "shave", "kolakavod", "todah", "todaraba", "yalla",
            "esh", "melech", "malka", "neshama", "motek", "kapara"
        ]
        kombina_slang_he = [
            "קומבינה", "פרוטקציה", "חבר", "חברים", "אחלה", "סבבה", "בוס",
            "פינוק", "מתנה", "שווה", "כלהכבוד", "תודה", "תודהרבה", "יאללה",
            "אש", "מלך", "מלכה", "נשמה", "מותק", "כפרה"
        ]

        # Cognitive Bias 3: Exclusivity, VIP & Authority Heuristic ("Perceived Status")
        status_authority_en = [
            "vip", "secret", "exclusive", "hidden", "private", "insider", "members",
            "gold", "platinum", "black", "prime", "pro", "club", "team", "crew",
            "owner", "manager"
        ]
        status_authority_he = [
            "ויאיפי", "סודי", "בלעדי", "מועדון", "זהב", "פלטינום", "מיוחד",
            "מיוחדת", "סופר", "צוות", "הנהלה", "מנהל"
        ]

        # Cognitive Bias 4: Life Milestones & Empathy Triggers ("Celebration Anchor")
        milestones_en = [
            "birthday", "bday", "mazaltov", "hatuna", "wedding", "kalla", "hatan",
            "brit", "barmitzvah", "batmitzvah", "giyus", "shihrur", "student", "pensioner"
        ]
        milestones_he = [
            "יוםהולדת", "יומהולדת", "מזלטוב", "חתונה", "כלה", "חתן", "ברית",
            "ברמצווה", "בתמצווה", "גיוס", "שחרור", "סטודנט", "גמלאי"
        ]

        # Cognitive Bias 5: National Resilience & Solidarity Heuristic ("In-Group Unity")
        solidarity_en = [
            "miluim", "miluimnik", "tzahal", "idf", "iron", "barzel", "yachad",
            "beyachad", "together", "israel", "amchai", "giborim", "heroes", "otef"
        ]
        solidarity_he = [
            "מילואים", "מילואימניק", "צהל", "ברזל", "יחד", "ביחד", "ישראל",
            "עםחי", "גיבורים", "עוטף"
        ]

        psychology_tokens = (
            family_circle_en + family_circle_he +
            kombina_slang_en + kombina_slang_he +
            status_authority_en + status_authority_he +
            milestones_en + milestones_he +
            solidarity_en + solidarity_he
        )

        psych_numbers = [10, 15, 20, 25, 30, 5, 50, 100]

        for token in psychology_tokens:
            raw_candidates.append(token)
            # Permute with both Suffix AND Prefix numbers
            for n in psych_numbers:
                raw_candidates.append(f"{token}{n}")       # pinuk10, פינוק10
                raw_candidates.append(f"{n}{token}")       # 10pinuk, 10פינוק
                raw_candidates.append(f"{token}-{n}")      # pinuk-10
                raw_candidates.append(f"{n}-{token}")      # 10-pinuk
            for y in modern_years:
                raw_candidates.append(f"{token}{y}")       # pinuk2024, pinuk24
                raw_candidates.append(f"{y}{token}")       # 2024pinuk, 24pinuk


        # ======================================================================
        # 30. Optional Leetspeak Mutation Generator
        # ======================================================================
        if include_leetspeak:
            leet_map = {"e": "3", "a": "4", "o": "0", "s": "5", "i": "1"}
            leet_additions = []
            for item in raw_candidates[:250]:
                mutated = item
                for char, sub in leet_map.items():
                    mutated = mutated.replace(char, sub)
                if mutated != item:
                    leet_additions.append(mutated)
            raw_candidates.extend(leet_additions)

        # ======================================================================
        # 31. Deduplication while strictly preserving exact priority order
        # ======================================================================
        seen = set()
        deduped = []
        for c in raw_candidates:
            code = c.strip().lower().replace(" ", "")
            if code and code not in seen:
                seen.add(code)
                deduped.append(code)

        return deduped
