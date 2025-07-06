import argparse

class Character:
    def __init__(self, name: str, alignment: str, hp: int):
        self.name = name
        self._alignment = alignment
        self._hp = hp

    def print_character_details(self) -> None:
        print(f"{self.name} alignment: {self._alignment}")

    
class Player(Character):
    def __init__(
        self,
        name: str,
        alignment: str,
        hp: int,
        defence: int,
        inventory: int,
        lives: int,
        redo: int
    ):
        super().__init__(name, alignment, hp)
        self._defence = defence
        self._inventory = inventory
        self._lives = lives
        self._redo = redo
    
    def print_player_status(self) -> None:
        print(f"HP: {self._hp} Def: {self._defence}")

class Game:
    def __init__(self, player: Player):
        self.player = player
        self.active = True

    def print_player(self):
        self.player.print_character_details()
        self.player.print_player_status()

    def game_loop(self):
        while self.active:
            input("start...")
        
def main(args):
    player = Player(args.name, args.align, 100, 10, 5, 3, 1)
    Game(player).game_loop()

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--name", action="store")
    parser.add_argument('-a', "--align", default="good", choices=['good', 'bad'])

    args = parser.parse_args()

    main(args)