import json
import random
from pathlib import Path
from tkinter import *
from PIL import Image, ImageTk

import sys

if getattr(sys, "frozen", False):
    # PyInstaller által becsomagolt futtatáskor itt vannak kicsomagolva a fájlok
    BASE_DIR = Path(sys._MEIPASS)
else:
    # Normál futtatás PyCharmból
    BASE_DIR = Path(__file__).resolve().parent
with open(BASE_DIR / "cards.json", "r") as file:
    data = json.load(file)
values={
        "K":10,
        "Q":10,
        "J":10,
        "10":10,
        "9":9,
        "8":8,
        "7":7,
        "6":6,
        "5":5,
        "4":4,
        "3":3,
        "2":2
    }

deck = []
deck_count = 1
shoe_size = 0
dealerhand = []
playerhands = []
hand_bets = []
finished_hands = []
current_hand = 0
round_active = False
card_images = {}
bankroll = 1000.0
stats = {"rounds": 0, "wins": 0, "losses": 0, "pushes": 0}
insurance_pending = False
insurance_taken = False
insurance_bet = 0.0
##############################
##############################
##############################
#         game logic         #
##############################
##############################
##############################
def osztas(deck:list):
    kartya= deck[0]
    deck.pop(0)
    return kartya

def value(hand: list):
    total = 0
    aces = 0

    for card in hand:
        if card["name"] == "A":
            total += 11
            aces += 1
        else:
            total += values[card["name"]]

    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    return total


def game_start():
    global deck, deck_count, shoe_size, dealerhand, playerhands, hand_bets
    global finished_hands, current_hand, round_active, bankroll
    global insurance_pending, insurance_taken, insurance_bet

    try:
        opening_bet = float(bet_entry.get().replace(",", "."))
        if opening_bet <= 0 or opening_bet > bankroll:
            raise ValueError
    except ValueError:
        statuslabel.config(text="Adj meg érvényes tétet az egyenlegeden belül.")
        return

    if not deck:
        try:
            deck_count = int(deck_count_entry.get())
            if deck_count < 1:
                raise ValueError
        except ValueError:
            statuslabel.config(text="A paklik száma legalább 1 legyen.")
            return

        deck = data["cards"] * deck_count
        shoe_size = len(deck)
        random.shuffle(deck)
        deck_count_entry.config(state=DISABLED)

    if len(deck) <= shoe_size // 2:
        deck = data["cards"] * deck_count
        random.shuffle(deck)
        statuslabel.config(text=f"Új shoe keverve: {deck_count} pakli.")

    dealerhand = []
    playerhands = [[]]
    bankroll -= opening_bet
    hand_bets = [opening_bet]
    insurance_bet = 0.0
    insurance_taken = False
    finished_hands = [False]
    current_hand = 0
    round_active = True
    update_money_display()

    startbtn.place_forget()
    playerhands[0].append(osztas(deck))
    dealerhand.append(osztas(deck))
    playerhands[0].append(osztas(deck))
    dealerhand.append(osztas(deck))

    updatevalue(value(playerhands[0]), value([dealerhand[0]]))
    draw_cards(reveal_dealer=False, animated_targets={
        ("player", 0, 0), ("dealer", 0), ("player", 0, 1), ("dealer", 1)
    })
    if len(deck) > shoe_size // 2:
        statuslabel.config(text=f"Válassz okosan: Hit, Stand, Double or Split. "
                               f"Lapok maradtak: {len(deck)}")
    update_buttons()

    insurance_pending = dealerhand[0]["name"] == "A"
    if insurance_pending:
        statuslabel.config(
            text="Dealer ász látható. Kérsz insurance-t? (a tét fele)")
        update_buttons()
        return

    # A natural blackjack ends the round before any action is possible.
    if value(playerhands[0]) == 21:
        finish_current_hand()

def updatevalue(player,dealer):
    playervaluebtn.config(text=f"{player}")
    dealervaluebtn.config(text=f"{dealer}")

def update_money_display():
    bankroll_label.config(text=f"Egyenleg: ${bankroll:,.2f}")
    stats_label.config(
        text=f"Körök: {stats['rounds']}  |  W: {stats['wins']}  L: "
             f"{stats['losses']}  D: {stats['pushes']}")
    if bankroll <= 0 and not round_active:
        startbtn.config(state=DISABLED)

def resolve_insurance():
    global insurance_pending, insurance_taken, insurance_bet, bankroll

    if not insurance_pending:
        return
    insurance_pending = False
    insurance_taken = True
    insurance_bet = hand_bets[0] / 2
    if bankroll < insurance_bet:
        insurance_taken = False
        insurance_bet = 0.0
        statuslabel.config(text="Nincs elég pénz az insurance megkötéséhez.")
    else:
        bankroll -= insurance_bet
        statuslabel.config(text="Insurance megkötve. Folytasd a játékot.")
    update_money_display()
    update_buttons()
    if value(playerhands[0]) == 21:
        finish_current_hand()

def decline_insurance():
    global insurance_pending

    if not insurance_pending:
        return
    insurance_pending = False
    statuslabel.config(text="Insurance elutasítva. Folytasd a játékot.")
    update_buttons()
    if value(playerhands[0]) == 21:
        finish_current_hand()

def card_filename(card):
    names = {"A": "ace", "J": "jack", "Q": "queen", "K": "king"}
    name = names.get(card["name"], card["name"])
    return BASE_DIR / "cards" / f"{name}_of_{card['suit']}.png"

def draw_cards(reveal_dealer=True, animated_targets=None):
    animated_targets = animated_targets or set()
    canvas.delete("card")
    canvas.delete("hand_panel")
    canvas.delete("shoe")
    card_images.clear()

    shoe_x, shoe_y = 548, 245
    for offset in range(4):
        canvas.create_rectangle(shoe_x - offset * 2, shoe_y - offset * 2,
                                shoe_x + 70 - offset * 2,
                                shoe_y + 105 - offset * 2,
                                fill="#1e3a8a", outline="#93c5fd",
                                width=1, tags="shoe")
    canvas.create_text(shoe_x + 35, shoe_y + 120, text="PAKLI",
                       fill="#bbf7d0", font=("Segoe UI", 8, "bold"),
                       tags="shoe")

    for index, card in enumerate(dealerhand):
        x, y = 170 + index * 80, 180
        if index == 1 and not reveal_dealer:
            is_animated = ("dealer", index) in animated_targets
            start_x = shoe_x if is_animated else x
            start_y = shoe_y if is_animated else y
            card_id = canvas.create_rectangle(start_x, start_y, start_x + 70,
                                              start_y + 105, fill="#1e3a8a",
                                              outline="#bfdbfe", width=2,
                                              tags="card")
            question_id = canvas.create_text(start_x + 35, start_y + 52,
                                             text="?", fill="white",
                                             font=("Segoe UI", 22, "bold"),
                                             tags="card")
            if is_animated:
                animate_card_to(card_id, x, y, 100)
                animate_card_to(question_id, x + 35, y + 52, 100)
        else:
            image = Image.open(card_filename(card)).resize((70, 105))
            card_images[f"dealer{index}"] = ImageTk.PhotoImage(image)
            is_animated = ("dealer", index) in animated_targets
            card_id = canvas.create_image(shoe_x if is_animated else x,
                                          shoe_y if is_animated else y,
                                          image=card_images[f"dealer{index}"],
                                          anchor="nw", tags="card")
            if is_animated:
                animate_card_to(card_id, x, y, 100)

    is_split = len(playerhands) > 1
    if is_split:
        hand_positions = [145, 385]
        for hand_index, x in enumerate(hand_positions):
            active = hand_index == current_hand and round_active
            panel_color = "#14532d" if active else "#0f3d25"
            border_color = "#facc15" if active else "#15803d"
            canvas.create_rectangle(x - 18, 397, x + 170, 555,
                                    fill=panel_color, outline=border_color,
                                    width=2, tags="hand_panel")
            canvas.create_text(x + 76, 415, text=f"HAND {hand_index + 1}",
                               fill="#fef08a" if active else "#bbf7d0",
                               font=("Segoe UI", 9, "bold"),
                               tags="hand_panel")

    for hand_index, hand in enumerate(playerhands):
        for index, card in enumerate(hand):
            card_width, card_height = (58, 87) if is_split else (70, 105)
            image = Image.open(card_filename(card)).resize(
                                          (card_width, card_height))
            key = f"player{hand_index}{index}"
            card_images[key] = ImageTk.PhotoImage(image)
            x = (145 + index * 34 + hand_index * 240
                                           if is_split else 170 + index * 80)
            y = 435 if is_split else 405
            is_animated = ("player", hand_index, index) in animated_targets
            card_id = canvas.create_image(
                                          shoe_x if is_animated else x,
                                          shoe_y if is_animated else y,
                                          image=card_images[key],
                                          anchor="nw", tags="card")
            if is_animated:
                                          animate_card_to(card_id, x, y, 100)


def animate_card_to(item_id, target_x, target_y, delay=0, steps=12):
    if delay > 0:
        canvas.after(delay, animate_card_to, item_id, target_x, target_y,
                     0, steps)
        return
    if steps == 0:
        return
    current = canvas.coords(item_id)
    if len(current) < 2:
        return
    dx = (target_x - current[0]) / steps
    dy = (target_y - current[1]) / steps
    canvas.move(item_id, dx, dy)
    canvas.after(16, animate_card_to, item_id, target_x, target_y, 0,
                 steps - 1)

def update_buttons():
    active = (round_active and not insurance_pending and playerhands
              and not finished_hands[current_hand])
    can_split = (
        active
        and len(playerhands) == 1
        and len(playerhands[current_hand]) == 2
        and playerhands[current_hand][0]["name"] ==
        playerhands[current_hand][1]["name"]
    )
    can_double = active and len(playerhands[current_hand]) == 2

    state = NORMAL if active else DISABLED
    splitbtn.place_forget()
    standbtn.place_forget()
    hitbtn.place_forget()
    doublebtn.place_forget()
    hitbtn.config(state=state)
    standbtn.config(state=state)
    doublebtn.config(state=NORMAL if can_double else DISABLED)
    splitbtn.config(state=NORMAL if can_split else DISABLED)
    insurancebtn.place_forget()
    noinsurancebtn.place_forget()
    if insurance_pending:
        insurancebtn.place(x=245, y=555)
        noinsurancebtn.place(x=395, y=555)
        insurancebtn.config(state=NORMAL if bankroll >= hand_bets[0] / 2
                            else DISABLED)
    else:
        splitbtn.place(x=55, y=555)
        standbtn.place(x=210, y=555)
        hitbtn.place(x=365, y=555)
        doublebtn.place(x=520, y=555)

def draw_for_current_hand():
    card_index = len(playerhands[current_hand])
    playerhands[current_hand].append(osztas(deck))
    updatevalue(value(playerhands[current_hand]), value([dealerhand[0]]))
    draw_cards(reveal_dealer=False,
               animated_targets={("player", current_hand, card_index)})

def next_hand_or_dealer():
    global current_hand

    for index in range(current_hand + 1, len(playerhands)):
        if not finished_hands[index]:
            current_hand = index
            updatevalue(value(playerhands[current_hand]), value([dealerhand[0]]))
            draw_cards(reveal_dealer=False)
            statuslabel.config(text=f"Playing hand {current_hand + 1}.")
            update_buttons()
            return

    dealer_turn()

def settle_round(dealer_value):
    global bankroll

    round_wins = round_losses = round_pushes = 0
    payouts = []
    dealer_blackjack = len(dealerhand) == 2 and dealer_value == 21
    if insurance_taken and dealer_blackjack:
        bankroll += insurance_bet * 3

    for hand, bet in zip(playerhands, hand_bets):
        player_value = value(hand)
        natural = len(hand) == 2 and player_value == 21
        if player_value > 21:
            result, payout = "losses", 0
        elif natural and not dealer_blackjack:
            result, payout = "wins", bet * 2.5
        elif dealer_value > 21 or player_value > dealer_value:
            result, payout = "wins", bet * 2
        elif player_value == dealer_value:
            result, payout = "pushes", bet
        else:
            result, payout = "losses", 0

        bankroll += payout
        payouts.append((player_value, result))
        if result == "wins":
            round_wins += 1
        elif result == "losses":
            round_losses += 1
        else:
            round_pushes += 1

    stats["rounds"] += 1
    stats["wins"] += round_wins
    stats["losses"] += round_losses
    stats["pushes"] += round_pushes
    update_money_display()
    return payouts

def finish_current_hand():
    if not round_active or finished_hands[current_hand]:
        return

    finished_hands[current_hand] = True
    next_hand_or_dealer()

def dealer_turn():
    global round_active

    first_new_card = len(dealerhand)
    while value(dealerhand) < 17:
        dealerhand.append(osztas(deck))

    dealer_value = value(dealerhand)
    updatevalue(value(playerhands[current_hand]), dealer_value)
    draw_cards(
        reveal_dealer=True,
        animated_targets={("dealer", index)
                           for index in range(first_new_card, len(dealerhand))}
    )

    results = settle_round(dealer_value)

    round_active = False
    update_money_display()
    statuslabel.config(text=f"Dealer: {dealer_value}. " +
                       " | ".join(f"Hand {i + 1}: {value} {result}"
                                  for i, (value, result) in enumerate(results)) +
                       f"   Lapok maradtak: {len(deck)}")
    startbtn.place(x=286, y=302)
    update_buttons()

def hit():
    if not round_active:
        return
    draw_for_current_hand()
    hand_value = value(playerhands[current_hand])
    if hand_value > 21:
        statuslabel.config(text=f"Hand {current_hand + 1} busts.")
        finish_current_hand()
    elif hand_value == 21:
        finish_current_hand()

def stand():
    if round_active:
        finish_current_hand()

def double():
    global bankroll

    if (not round_active or len(playerhands[current_hand]) != 2 or
            bankroll < hand_bets[current_hand]):
        return
    bankroll -= hand_bets[current_hand]
    hand_bets[current_hand] *= 2
    update_money_display()
    draw_for_current_hand()
    if value(playerhands[current_hand]) > 21:
        statuslabel.config(text=f"Hand {current_hand + 1} busts after doubling.")
    finish_current_hand()

def split():
    global current_hand, playerhands, hand_bets, finished_hands, bankroll

    if (not round_active or len(playerhands) != 1 or
            len(playerhands[0]) != 2 or
            playerhands[0][0]["name"] != playerhands[0][1]["name"]):
        return
    if bankroll < hand_bets[0]:
        statuslabel.config(text="Splithez nincs elég pénz az egyenlegen.")
        return

    first_card, second_card = playerhands[0]
    bankroll -= hand_bets[0]
    playerhands = [[first_card], [second_card]]
    hand_bets = [hand_bets[0], hand_bets[0]]
    finished_hands = [False, False]
    current_hand = 0
    update_money_display()
    playerhands[0].append(osztas(deck))
    playerhands[1].append(osztas(deck))
    updatevalue(value(playerhands[0]), value([dealerhand[0]]))
    draw_cards(reveal_dealer=False, animated_targets={
        ("player", 0, 1), ("player", 1, 1)
    })
    statuslabel.config(text="Hand 1 split. Playing hand 1.")
    update_buttons()


##############################
##############################
##############################
#         window stuff       #
##############################
##############################
##############################
height = 700
width = 700
root = Tk()

root.title("Blackjack")
root.configure(bg="#101722")
root.minsize(width, height)
root.maxsize(width, height)
root.resizable(False, False)

canvas = Canvas(root, bg="#101722", height=height, width=width,
                highlightthickness=0)
canvas.create_text(350, 24, text="BLACKJACK", fill="#f8fafc",
                   font=("Segoe UI", 18, "bold"))
canvas.create_text(350, 48, text="Készen állsz a következő körre?",
                   fill="#94a3b8", font=("Segoe UI", 9))

# Layered table gives the playing area a subtle frame and depth.
canvas.create_oval(44, 88, 656, 618, fill="#334155", outline="")
canvas.create_oval(55, 98, 645, 608, fill="#14532d", outline="#22c55e",
                   width=2)
canvas.create_oval(72, 115, 628, 591, fill="#166534", outline="#15803d",
                   width=2)
canvas.create_line(155, 352, 545, 352, fill="#22c55e", width=1)
canvas.create_text(350, 132, text="DEALER", fill="#bbf7d0",
                   font=("Segoe UI", 10, "bold"))
canvas.create_text(350, 380, text="PLAYER", fill="#bbf7d0",
                   font=("Segoe UI", 10, "bold"))

button_font = ("Segoe UI", 10, "bold")
button_base = {
    "width": 10, "height": 2, "font": button_font,
    "relief": SOLID, "bd": 2, "cursor": "hand2",
    "highlightthickness": 2, "highlightcolor": "#f8fafc",
    "activeforeground": "#ffffff"
}
splitbtn = Button(root, text="SPLIT", bg="#334155", fg="#e2e8f0",
                  activebackground="#475569", command=split, **button_base)
standbtn = Button(root, text="STAND", bg="#7f1d1d", fg="#fee2e2",
                  activebackground="#991b1b", command=stand, **button_base)
hitbtn = Button(root, text="HIT", bg="#166534", fg="#dcfce7",
                activebackground="#15803d", command=hit, **button_base)
doublebtn = Button(root, text="DOUBLE", bg="#92400e", fg="#fef3c7",
                   activebackground="#b45309", command=double, **button_base)
insurancebtn = Button(root, text="INSURANCE", bg="#7c3aed", fg="#f5f3ff",
                      activebackground="#8b5cf6", command=resolve_insurance,
                      **button_base)
noinsurancebtn = Button(root, text="NO INSURANCE", bg="#475569",
                        fg="#f1f5f9", activebackground="#64748b",
                        command=decline_insurance, **button_base)
startbtn = Button(root, text="START ROUND", bg="#2563eb", fg="#eff6ff",
                  activebackground="#3b82f6", command=game_start,
                  width=14, height=2, font=button_font, relief=FLAT,
                  bd=0, cursor="hand2", highlightthickness=2,
                  highlightbackground="#93c5fd",
                  highlightcolor="#ffffff")

statuslabel = Label(root, text="Nyomd meg a START ROUND gombot az osztáshoz.",
                    bg="#1e293b", fg="#e2e8f0", width=72, height=2,
                    anchor="center", font=("Segoe UI", 9))
settings_frame = Frame(root, bg="#172033", highlightbackground="#475569",
                       highlightthickness=1, bd=0)
deck_count_label = Label(settings_frame, text="Paklik", bg="#172033",
                         fg="#cbd5e1", font=("Segoe UI", 9))
deck_count_entry = Entry(settings_frame, width=5, justify="center",
                         bg="#0f172a", fg="#f8fafc", insertbackground="white",
                         relief=SOLID, bd=1, font=("Segoe UI", 10, "bold"),
                         highlightthickness=1, highlightbackground="#64748b")
deck_count_entry.insert(0, "1")
bet_label = Label(settings_frame, text="Tét", bg="#172033", fg="#cbd5e1",
                  font=("Segoe UI", 9))
bet_entry = Entry(settings_frame, width=7, justify="center", bg="#0f172a",
                  fg="#f8fafc", insertbackground="white", relief=FLAT, bd=0,
                  font=("Segoe UI", 10, "bold"), highlightthickness=1,
                  highlightbackground="#64748b")
bet_entry.insert(0, "25")
bankroll_label = Label(root, text="", bg="#101722", fg="#facc15",
                       font=("Segoe UI", 10, "bold"))
stats_label = Label(root, text="", bg="#101722", fg="#94a3b8",
                    font=("Segoe UI", 8))

value_style = {
    "width": 3, "height": 1, "font": ("Segoe UI", 14, "bold"),
    "relief": FLAT, "bd": 0, "disabledforeground": "#0f172a"
}
dealervaluebtn = Button(root, text="0", bg="#facc15", fg="#0f172a",
                        **value_style)
playervaluebtn = Button(root, text="0", bg="#facc15", fg="#0f172a",
                        **value_style)

statuslabel.place(x=50, y=650)
settings_frame.place(x=45, y=610, width=300, height=34)
deck_count_label.place(x=10, y=8)
deck_count_entry.place(x=55, y=5, height=24)
bet_label.place(x=125, y=8)
bet_entry.place(x=155, y=5, height=24)
bankroll_label.place(x=375, y=614)
stats_label.place(x=375, y=635)
splitbtn.place(x=55, y=555)
standbtn.place(x=210, y=555)
hitbtn.place(x=365, y=555)
doublebtn.place(x=520, y=555)
dealervaluebtn.place(x=565, y=166)
playervaluebtn.place(x=565, y=414)
startbtn.place(x=286, y=302)

canvas.pack()
update_money_display()
update_buttons()
root.mainloop()