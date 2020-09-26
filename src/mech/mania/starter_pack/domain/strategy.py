import logging

from mech.mania.starter_pack.domain.model.characters.character_decision import CharacterDecision
from mech.mania.starter_pack.domain.model.characters.position import Position
from mech.mania.starter_pack.domain.model.characters.player import Player
from mech.mania.starter_pack.domain.model.game_state import GameState
from mech.mania.starter_pack.domain.api import API


class Strategy:
    def __init__(self, memory):
        self.memory = memory
        self.logger = logging.getLogger('strategy')
        self.logger.setLevel(logging.DEBUG)
        logging.basicConfig(level = logging.INFO)

    def make_decision(self, player_name: str, game_state: GameState) -> CharacterDecision:
        """
        Parameters:
        player_name (string): The name of your player
        game_state (GameState): The current game state
        """
        self.api = API(game_state, player_name)
        self.my_player = game_state.get_all_players()[player_name]
        self.board = game_state.get_pvp_board()
        self.curr_pos = self.my_player.get_position()
        self.game_state = game_state

        self.logger.info("In make_decision")

        self.logger.info(f"Currently at position: ({self.curr_pos.x},{self.curr_pos.y}) on board '{self.curr_pos.board_id}'")

        monster_list = self.crappy_find_enemies_by_distance(self.curr_pos, name_filter="slime")
        close_mon = monster_list[0]
        dist = self.curr_pos.manhattan_distance(close_mon.get_position())
        self.logger.warn("Closest monster is %s at %d" % (close_mon.get_name(), dist))

        decision = None

        weapon = self.my_player.get_weapon()
        self.logger.warn("Weapon range: %d, attack %d" % (weapon.get_range(), weapon.get_attack()))

        if(dist > weapon.get_range()):
            new_pos = self.crappy_find_position_to_move(self.my_player, close_mon.get_position())
            decision = CharacterDecision(
                decision_type="MOVE",
                action_position=new_pos,
                action_index=0
            )
            self.logger.warn("Moving from (%d %d) => (%d %d)" % (self.curr_pos.x, self.curr_pos.y, new_pos.x, new_pos.y))
        else:
            decision = CharacterDecision(
                decision_type="ATTACK",
                action_position=close_mon.get_position(),
                action_index=0
            )
            self.logger.warn("Attacking %s" % close_mon.get_name())

        return decision

    def create_move_decision(self, dx, dy):
        new_pos = self.curr_pos.create(self.curr_pos.x + dx, self.curr_pos.y + dy, self.curr_pos.get_board_id())
        decision = CharacterDecision(
            decision_type="MOVE",
            action_position=new_pos,
            action_index=0
        )
        return decision

    def crappy_find_enemies_by_distance(self, pos, name_filter=""):
        curr_board = self.curr_pos.get_board_id()
        monsters = self.game_state.get_monsters_on_board(curr_board)
        distances = [mon for mon in monsters if not mon.is_dead() and name_filter in mon.get_name().lower()]

        distances.sort(key=lambda mon: pos.manhattan_distance(mon.get_position()))
        return distances

    def crappy_find_position_to_move(self, player, destination) -> Position:
        x_dist = destination.x - player.get_position().x
        y_dist = destination.y - player.get_position().y

        dx = 0
        dy = 0

        if abs(x_dist) > abs(y_dist):
            if x_dist != 0:
                dx = int(abs(x_dist) / x_dist)
        else:
            if y_dist != 0:
                dy = int(abs(y_dist) / y_dist)

        new_pos = self.curr_pos.create(player.get_position().x + dx, player.get_position().y + dy, self.curr_pos.get_board_id())

        return new_pos

    # feel free to write as many helper functions as you need!
    def find_position_to_move(self, player: Player, destination: Position) -> Position:
        path = self.api.find_path(player.get_position(), destination)
        # path can be empty if player.get_position() == destination
        if len(path) == 0:
            return player.get_position()
        pos = None
        if len(path) < player.get_speed():
            pos = path[-1]
        else:
            pos = path[player.get_speed() - 1]
        return pos
