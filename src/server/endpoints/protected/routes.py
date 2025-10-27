import random
from flask import Blueprint, request, jsonify, render_template   # ← añade render_template
from flask_login import login_required, current_user
from models import db, User, Estadistica

# --- Blueprint de PÁGINA (para /ruleta y endpoint 'ruleta.home') ---
bp = Blueprint('ruleta', __name__)

@bp.route('/ruleta')
@login_required
def home():
    return render_template('ruleta.html')

# --- Blueprint de API (para /api/ruleta/...) ---
bp_ruleta = Blueprint("bp_ruleta", __name__, url_prefix="/api/ruleta")

def _sync_balance_from_cents(user):
    try:
        user.balance = (user.saldo_centimos or 0) / 100.0
    except Exception:
        user.balance = 0.0

EURO_SEQ = [0,32,15,19,4,21,2,25,17,34,6,27,13,36,11,30,8,23,10,5,24,16,33,1,20,14,31,9,22,18,29,7,28,12,35,3,26]
REDS = set([1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36])
PAYOUT = {"straight":35, "split":17, "street":11, "corner":8, "line":5, "dozen":2, "column":2, "even":1}

def _get_stats(user_id):
    st = Estadistica.query.filter_by(user_id=user_id, juego='ruleta').first()
    if not st:
        st = Estadistica(user_id=user_id, juego='ruleta')
        db.session.add(st)
        db.session.flush()
    return st

@bp_ruleta.get("/state")
@login_required
def state():
    st = _get_stats(current_user.id)
    cents = getattr(current_user, "saldo_centimos", 0)
    if not cents:
        try:
            cents = int(round((getattr(current_user, "balance", 0.0) or 0.0) * 100))
        except Exception:
            cents = 0
    return jsonify({
        "ok": True,
        "balance": cents,  # céntimos
        "stats": {
            "spins": getattr(st, "spins", 0),
            "bet_cents": getattr(st, "bet_cents", 0),
            "win_cents": getattr(st, "win_cents", 0),
            "returned_cents": getattr(st, "returned_cents", 0),
            "net_cents": getattr(st, "net_cents", 0),
        }
    })

@bp_ruleta.post("/place")
@login_required
def place():
    data = request.get_json(force=True) or {}
    bets = data.get("bets") or []
    min_cell = int(data.get("min_cell", 20))

    total = 0
    for b in bets:
        amount = int(b.get("amount", 0))
        if amount < min_cell:
            return jsonify({"ok": False, "error": f"Apuesta mínima: {min_cell}¢"}), 400
        total += amount

    if getattr(current_user, "saldo_centimos", 0) < total:
        return jsonify({"ok": False, "error": "Fondos insuficientes"}), 400

    current_user.saldo_centimos -= total
    _sync_balance_from_cents(current_user)
    db.session.commit()

    import time
    return jsonify({
        "ok": True,
        "session_id": int(time.time() * 1000),
        "balance": current_user.saldo_centimos
    })

@bp_ruleta.post("/spin")
@login_required
def spin():
    data = request.get_json(force=True) or {}
    bets = data.get("bets") or []
    if not bets:
        return jsonify({"ok": False, "error": "Faltan apuestas"}), 400

    # resultado que manda el front para que coincida con la animación
    client_result = data.get("result", None)
    try:
        result = int(client_result) if client_result is not None else random.choice(EURO_SEQ)
    except Exception:
        result = random.choice(EURO_SEQ)

    returned = 0
    win = 0

    def is_red(n): return n in REDS
    def is_black(n): return (n != 0) and (n not in REDS)
    def is_even(n): return (n != 0) and (n % 2 == 0)
    def is_odd(n):  return (n % 2 == 1)

    for b in bets:
        btype = b.get("type")
        amount = int(b.get("amount", 0))
        cov = set(b.get("set") or [])
        if btype == "even":
            lbl = (b.get("label") or "").lower()
            if lbl == "rojo":     hit = is_red(result)
            elif lbl == "negro":  hit = is_black(result)
            elif lbl == "par":    hit = is_even(result)
            elif lbl == "impar":  hit = is_odd(result)
            elif lbl in ("1–18","1-18"):   hit = 1 <= result <= 18
            elif lbl in ("19–36","19-36"): hit = 19 <= result <= 36
            else:                   hit = result in cov
        else:
            hit = result in cov

        if hit:
            mult = PAYOUT.get(btype, 0)
            win += amount * mult
            returned += amount

    current_user.saldo_centimos += (returned + win)
    _sync_balance_from_cents(current_user)

    st = _get_stats(current_user.id)
    st.spins = (getattr(st, "spins", 0) + 1)
    total_bet = sum(int(b["amount"]) for b in bets)
    st.bet_cents = getattr(st, "bet_cents", 0) + total_bet
    st.win_cents = getattr(st, "win_cents", 0) + win
    st.returned_cents = getattr(st, "returned_cents", 0) + returned
    st.net_cents = (getattr(st, "win_cents", 0) + getattr(st, "returned_cents", 0)) - getattr(st, "bet_cents", 0)

    db.session.commit()

    return jsonify({
        "ok": True,
        "result": result,
        "payout": win,
        "returned": returned,
        "balance": current_user.saldo_centimos,
        "stats": {
            "spins": getattr(st, "spins", 0),
            "bet_cents": getattr(st, "bet_cents", 0),
            "win_cents": getattr(st, "win_cents", 0),
            "returned_cents": getattr(st, "returned_cents", 0),
            "net_cents": getattr(st, "net_cents", 0),
        }
    })
