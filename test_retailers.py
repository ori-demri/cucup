import json
from models import TriageStatus
from strategies import get_retailer_strategy, TalronStrategy, OrlandoStrategy
from wordlist import WordlistEngine


def test_strategy_factory():
    talron = get_retailer_strategy("talron")
    assert isinstance(talron, TalronStrategy)
    assert talron.name == "talron"
    assert "tal-ron.co.il" in talron.target_url

    orlando = get_retailer_strategy("orlando")
    assert isinstance(orlando, OrlandoStrategy)
    assert orlando.name == "orlando"
    assert "orlando.co.il" in orlando.target_url
    assert "fkcart_apply_coupon" in orlando.target_url
    print("[PASS] Strategy factory tests passed.")


def test_payload_builder():
    talron = TalronStrategy()
    t_payload = talron.build_payload("CODE1", "nonce123")
    assert t_payload == {
        "security": "nonce123",
        "coupon_code": "CODE1",
        "billing_email": "",
    }

    orlando = OrlandoStrategy()
    o_payload = orlando.build_payload("CODE2", "nonce456")
    assert o_payload == {
        "discount_code": "CODE2",
        "nonce": "nonce456",
    }
    print("[PASS] Payload builder tests passed.")


def test_orlando_triage():
    orlando = OrlandoStrategy()

    # 1. Happy path (new30 / welcome5)
    happy_json = json.dumps({"status": True, "code": 200, "message": "\n\tקוד קופון הוחל בהצלחה.\t\n"})
    valid, status, msg = orlando.triage_response(happy_json, 200)
    assert valid is True
    assert status == TriageStatus.APPLIED
    assert "קוד קופון הוחל בהצלחה" in msg

    # 2. Invalid code
    invalid_json = json.dumps({"msg": 'לא ניתן לממש את הקופון "fake" מאחר שהוא לא קיים.', "code": 400})
    valid, status, msg = orlando.triage_response(invalid_json, 200)
    assert valid is False
    assert status == TriageStatus.INVALID

    # 3. Already applied
    already_json = json.dumps({"msg": 'קוד קופון זה כבר הוחל בסל.', "code": 400})
    valid, status, msg = orlando.triage_response(already_json, 200)
    assert valid is True
    assert status == TriageStatus.ALREADY_APPLIED

    # 4. Restricted (e.g. min spend)
    restricted_json = json.dumps({"msg": 'הסכום המינימלי להזמנה הוא 200 ₪ כדי להשתמש בקופון זה.', "code": 400})
    valid, status, msg = orlando.triage_response(restricted_json, 200)
    assert valid is True
    assert status == TriageStatus.RESTRICTED
    assert "Exists (conditional)" in msg

    # 5. Nonce expired / 403
    valid, status, msg = orlando.triage_response("-1", 403)
    assert valid is False
    assert status == TriageStatus.EXPIRED_NONCE
    print("[PASS] Orlando triage tests passed.")


def test_talron_triage():
    talron = TalronStrategy()

    # Success HTML
    success_html = '<div class="woocommerce-message">קוד הקופון הוחל בהצלחה.</div>'
    valid, status, msg = talron.triage_response(success_html, 200)
    assert valid is True
    assert status == TriageStatus.APPLIED

    # Invalid HTML
    invalid_html = '<ul class="woocommerce-error"><li>קוד הקופון "fake" אינו קיים!</li></ul>'
    valid, status, msg = talron.triage_response(invalid_html, 200)
    assert valid is False
    assert status == TriageStatus.INVALID
    print("[PASS] Talron triage tests passed.")


def test_ringer_triage():
    from strategies.ringer import RingerStrategy
    ringer = RingerStrategy()

    # Success JSON
    success_json = json.dumps({"success": True, "text": "הקופון נוסף בהצלחה", "coupon_code": ["welcome5"]})
    valid, status, msg = ringer.triage_response(success_json, 200)
    assert valid is True
    assert status == TriageStatus.APPLIED
    assert "הקופון נוסף בהצלחה" in msg

    # Already in cart (WordPress returns '0')
    valid, status, msg = ringer.triage_response("0", 200)
    assert valid is True
    assert status == TriageStatus.ALREADY_APPLIED

    # Invalid code
    invalid_json = json.dumps({"error": True, "error_message": "קוד שהזנת לא תקין "})
    valid, status, msg = ringer.triage_response(invalid_json, 200)
    assert valid is False
    assert status == TriageStatus.INVALID

    # Nonce expired / 403
    valid, status, msg = ringer.triage_response("-1", 403)
    assert valid is False
    assert status == TriageStatus.EXPIRED_NONCE
    print("[PASS] Ringer triage tests passed.")


def test_spring_triage():
    from strategies.spring import SpringStrategy
    spring = SpringStrategy()

    # Success HTML
    success_html = '<div class="woocommerce-message">קוד הקופון הוחל בהצלחה.</div>'
    valid, status, msg = spring.triage_response(success_html, 200)
    assert valid is True
    assert status == TriageStatus.APPLIED

    # Expired / Restricted code
    restricted_html = '<ul class="woocommerce-error" role="alert"><li>הקופון "spring10" פג תוקף.</li></ul>'
    valid, status, msg = spring.triage_response(restricted_html, 200)
    assert valid is True
    assert status == TriageStatus.RESTRICTED
    assert "spring10" in msg

    # Invalid code
    invalid_html = '<ul class="woocommerce-error" role="alert"><li>לא ניתן לממש את הקופון "dasd" מאחר שהוא לא קיים.</li></ul>'
    valid, status, msg = spring.triage_response(invalid_html, 200)
    assert valid is False
    assert status == TriageStatus.INVALID

    # Nonce expired / 403
    valid, status, msg = spring.triage_response("-1", 403)
    assert valid is False
    assert status == TriageStatus.EXPIRED_NONCE
    print("[PASS] Spring triage tests passed.")


def test_wordlists():
    talron = TalronStrategy()
    t_words = WordlistEngine.generate_candidates(strategy=talron)
    assert "talron50" in t_words
    assert "talron" in t_words
    assert "tal1" in t_words

    orlando = OrlandoStrategy()
    o_words = WordlistEngine.generate_candidates(strategy=orlando)
    assert "new30" in o_words
    assert "welcome5" in o_words
    assert "orlando" in o_words
    assert "orlando10" in o_words
    # Baseline test
    assert "new30" in orlando.baseline_candidates
    assert orlando.baseline_candidates[0] == "new30"

    # Default candidates tier test (without strategy passed)
    default_words = WordlistEngine.generate_candidates()
    assert "new30" in default_words
    assert default_words[0] == "new30"

    # Ringer wordlist test
    ringer = get_retailer_strategy("ringer")
    r_words = WordlistEngine.generate_candidates(strategy=ringer)
    assert "welcome5" in r_words
    assert "ringers" in r_words
    assert any("watch" in w for w in r_words)
    assert any("שעון" in w for w in r_words)

    # Spring / Avivs wordlist test
    spring = get_retailer_strategy("spring")
    s_words = WordlistEngine.generate_candidates(strategy=spring)
    assert "spring10" in s_words
    assert "aviv10" in s_words
    assert "spring" in s_words
    assert "avivs" in s_words
    assert "אביב" in s_words
    assert "ספרינג" in s_words
    assert any("shoes" in w for w in s_words)
    assert any("נעליים" in w for w in s_words)

    # Assert sale10, 20, 30, 40, 50 presence across default and all retailer candidates
    for p in [10, 20, 30, 40, 50]:
        assert f"sale{p}" in default_words, f"sale{p} missing from default candidates"
        assert f"sale{p}" in t_words, f"sale{p} missing from Talron candidates"
        assert f"sale{p}" in o_words, f"sale{p} missing from Orlando candidates"
        assert f"sale{p}" in r_words, f"sale{p} missing from Ringer candidates"
        assert f"sale{p}" in s_words, f"sale{p} missing from Spring candidates"

    # Assert user-specified priority patterns: {num}off, test{num}, save{num}
    for p in [10, 15, 20]:
        assert f"{p}off" in default_words
        assert f"save{p}" in default_words

    assert "10off" in default_words
    assert "test" in default_words
    assert "test10" in default_words
    assert "admin" in default_words
    assert "admin10" in default_words
    assert "employee" in default_words
    assert "military" in default_words
    assert "deal" in default_words
    assert "sorry" in default_words
    assert "freeshipping" in default_words
    assert "shipfree" in default_words
    assert "affiliate" in default_words
    assert "ambassador" in default_words
    assert "thankyou" in default_words
    assert "welcomeback" in default_words

    # Seasons
    assert "spring10" in default_words
    assert "summer20" in default_words
    assert "fall10" in default_words
    assert "winter20" in default_words
    assert "spring25" in default_words

    # US Holidays
    assert "turkey" in default_words
    assert "turkey10" in default_words
    assert "love" in default_words
    assert "valentine" in default_words
    assert "thanksgiving" in default_words

    # Jewish & Israeli Holidays (English & Hebrew)
    assert "passover" in default_words
    assert "passover10" in default_words
    assert "pesach" in default_words
    assert "purim" in default_words
    assert "purim10" in default_words
    assert "roshhashana" in default_words
    assert "sukkot" in default_words
    assert "hanukkah" in default_words
    assert "פסח" in default_words
    assert "פסח10" in default_words
    assert "פורים" in default_words
    assert "סוכות" in default_words
    assert "חנוכה" in default_words

    # Assert SimplyCodes Top 20 dataset patterns
    simplycodes_samples = [
        "10off50", "halfoff", "tenoff", "coffee", "specialoffers", "dayoff", "10offnow",
        "savemore", "savebig", "savenow", "save10now", "summersave", "springsave",
        "welcomeback", "welcomehome", "welcome10off", "welcomegift",
        "freeship", "shipsfree", "freedom", "free2day", "freebie", "ship4free",
        "newyear", "newsletter", "happynewyear", "newcustomer", "newlook", "newbie",
        "bfcm", "bfriday", "earlybf", "blackfriday", "blackout", "blackfriyay",
        "flashsale", "flashfriday", "summerflash",
        "buy2get1", "together", "bettertogether",
        "lovemom", "momsday", "thanksmom", "supermom",
        "july4", "4thofjuly", "christmasinjuly",
        "cybermonday", "cyberweek", "cybermon"
    ]
    for sc in simplycodes_samples:
        assert sc in default_words, f"SimplyCodes code '{sc}' missing from default wordlist"

    # Verify priority ordering: 10off should appear before test, save, admin, seasons, holidays
    idx_10off = default_words.index("10off")
    idx_test = default_words.index("test")
    idx_save10 = default_words.index("save10")
    idx_admin = default_words.index("admin")
    idx_turkey = default_words.index("turkey")
    idx_passover = default_words.index("passover")
    assert idx_10off < idx_test < idx_save10 < idx_admin < idx_turkey < idx_passover, (
        f"Ordering violated: 10off={idx_10off}, test={idx_test}, save10={idx_save10}, "
        f"admin={idx_admin}, turkey={idx_turkey}, passover={idx_passover}"
    )

    print(f"[PASS] Wordlist generation tests passed (Talron: {len(t_words)}, Orlando: {len(o_words)}, Ringer: {len(r_words)}, Spring: {len(s_words)}, Default: {len(default_words)}).")


if __name__ == "__main__":
    test_strategy_factory()
    test_payload_builder()
    test_orlando_triage()
    test_talron_triage()
    test_ringer_triage()
    test_spring_triage()
    test_wordlists()
    print("\nAll unit tests passed successfully!")
