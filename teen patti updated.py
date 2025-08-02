import random
import requests  # type: ignore 
from PIL import Image
from io import BytesIO
import time

def get_card_image(code):
    url = f"https://deckofcardsapi.com/static/img/{code}.png"
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
    return img

get_card_image("AS").show()

suits = ['♠', '♥', '♦', '♣']
ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
rank_values = {r: i for i, r in enumerate(ranks, 2)}

class Player:
    def __init__(self, name, is_human=False, chips=1000):
        self.name = name
        self.is_human = is_human
        self.chips = chips
        self.hand = []
        self.current_bet = 0
        self.active = True
        self.loan = 0
        self.seen = False

    def reset(self):
        self.hand = []
        self.current_bet = 0
        self.active = self.chips > 0
        self.seen = False

    def place_bet(self, amount):
        if self.chips >= amount:
            self.chips -= amount
            self.current_bet += amount
            return True
        return False

    def request_loan(self, amount, others):
        richest = max([p for p in others if p != self and p.chips >= amount], key=lambda x: x.chips, default=None)
        if richest:
            richest.chips -= amount
            self.chips += amount
            self.loan += amount
            print(f"{self.name} takes a loan of ₹{amount} from {richest.name}")
            return True
        return False

    def fold(self):
        self.active = False

    def show_hand(self):
        return ' '.join(self.hand) if self.active else "(Folded)"

def create_deck():
    return [r + s for s in suits for r in ranks]

def deal(deck):
    return [deck.pop() for _ in range(3)]

def hand_rank(hand):
    r = sorted([card[:-1] for card in hand], key=lambda x: rank_values[x])
    s = [card[-1] for card in hand]
    v = [rank_values[x] for x in r]
    unique = len(set(r))
    flush = len(set(s)) == 1
    seq = v == list(range(min(v), min(v)+3))

    if unique == 1: return (6, v)
    elif flush and seq: return (5, v)
    elif seq: return (4, v)
    elif flush: return (3, v)
    elif unique == 2: return (2, v)
    else: return (1, v)

def compare(p1, p2):
    return hand_rank(p1.hand) > hand_rank(p2.hand)

def bot_move(bot, max_chaal):
    if not bot.seen and random.random() < 0.2:
        return 'b'
    if bot.name == "Ram":
        return 'f' if random.random() < 0.3 else 'c'
    elif bot.name == "Shyam":
        return 's' if random.random() > 0.8 else 'c'
    return 'c'

def game_loop(players, boot=50, min_chaal=50, show_fee=100):
    deck = create_deck()
    random.shuffle(deck)

    pot = 0
    max_bet = boot

    for p in players:
        p.reset()
        if not p.place_bet(boot):
            if not p.request_loan(boot, players):
                p.fold()
        pot += boot

    for p in players:
        if p.active:
            p.hand = deal(deck)

    for rnd in range(5):
        for p in players:
            if not p.active:
                continue
            active = [x for x in players if x.active]
            if len(active) < 2:
                return settle(players, pot)

            print(f"\nPot: ₹{pot}")
            for x in players:
                status = "Seen" if x.seen else "Blind"
                print(f"{x.name}: ₹{x.chips}, Bet ₹{x.current_bet}, {status}, {'Active' if x.active else 'Folded'}")
                if x == p and x.is_human and x.seen:
                    print(f"Your cards: {x.show_hand()}")

            if p.is_human:
                if not p.seen:
                    if len(active) == 2:
                        move = input("Enter c=chaal (see cards), b=blind, s=show, f=fold: ").lower()
                    else:
                        move = input("Enter c=chaal (see cards), b=blind, f=fold: ").lower()
                else:
                    if len(active) == 2:
                        move = input("Enter c=chaal, s=show, f=fold: ").lower()
                    else:
                        move = input("Enter c=chaal, f=fold: ").lower()
            else:
                time.sleep(20)  # ⏱️ Dramatic pause
                print(f"\n{p.name} is thinking...")
                time.sleep(2)
                move = bot_move(p, max_bet)
                print(f"{p.name} chooses: {move}")

            if move == 'f':
                p.fold()

            elif move == 's' and len(active) == 2:
                if not p.place_bet(show_fee):
                    if not p.request_loan(show_fee, players):
                        print(f"{p.name} couldn't pay show fee. Folded.")
                        p.fold()
                        continue
                pot += show_fee
                return do_show(players, pot)

            elif move == 'b' and not p.seen:
                blind_amt = max(10, (max_bet // 2) + (max_bet % 2))
                if not p.place_bet(blind_amt):
                    if not p.request_loan(blind_amt, players):
                        print(f"{p.name} couldn't place blind. Folded.")
                        p.fold()
                        continue
                pot += blind_amt
                print(f"{p.name} plays blind for ₹{blind_amt}")
                continue

            elif move == 'c':
                p.seen = True
                if p.is_human:
                    print(f"\nYour cards: {p.show_hand()}")
                    decision = input(f"Do you want to chaal (min ₹{max_bet}) or fold? (c/f): ").lower()
                    if decision == 'f':
                        p.fold()
                        continue
                    try:
                        amt = int(input(f"Enter chaal amount (≥ ₹{max_bet}): "))
                        if amt < max_bet:
                            print("Too low. You folded.")
                            p.fold()
                            continue
                    except:
                        print("Invalid input. You folded.")
                        p.fold()
                        continue
                else:
                    amt = max_bet

                if not p.place_bet(amt):
                    if not p.request_loan(amt, players):
                        p.fold()
                        continue
                pot += amt
                if amt > max_bet:
                    max_bet = amt

    return settle(players, pot)

def do_show(players, pot):
    active = [p for p in players if p.active]
    if len(active) != 2:
        return settle(players, pot)
    p1, p2 = active
    print("\nSHOWDOWN!")
    print(f"{p1.name}: {p1.show_hand()} --> {hand_rank(p1.hand)}")
    print(f"{p2.name}: {p2.show_hand()} --> {hand_rank(p2.hand)}")
    winner = p1 if compare(p1, p2) else p2
    winner.chips += pot
    print(f"\n{winner.name} wins ₹{pot} by SHOW!")
    return

def settle(players, pot):
    active = [p for p in players if p.active]
    if len(active) == 1:
        active[0].chips += pot
        print(f"\n{active[0].name} wins ₹{pot} (others folded)")
    else:
        winner = active[0]
        for p in active[1:]:
            if compare(p, winner):
                winner = p
        winner.chips += pot
        print(f"\n{winner.name} wins ₹{pot}!")
    return

# Main loop
name = input("Enter your name: ")
players = [Player(name, True), Player("Ram"), Player("Shyam")]

while True:
    game_loop(players)
    print("\nBalances:")
    for p in players:
        print(f"{p.name}: ₹{p.chips} (Loan: ₹{p.loan})")
    again = input("\nPlay again? (y/n): ").lower()
    if again != 'y':
        print("Thanks for playing Teen Patti!")
        break
 



