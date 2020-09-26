import logging

from mech.mania.starter_pack.domain.model.characters.character_decision import CharacterDecision
from mech.mania.starter_pack.domain.model.characters.position import Position
from mech.mania.starter_pack.domain.model.characters.player import Player
from mech.mania.starter_pack.domain.model.game_state import GameState
from mech.mania.starter_pack.domain.api import API

from mech.mania.starter_pack.domain.model.items.weapon import Weapon


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

        last_action, type = self.memory.get_value("last_action", str)

        if last_action is not None and last_action == "PICKUP":
            self.logger.info("Last action was picking up, equipping picked up object")
            self.memory.set_value("last_action", "EQUIP")
            return CharacterDecision(
                decision_type="EQUIP",
                action_position=None,
                action_index=0  # self.my_player.get_free_inventory_index()
            )

        weapon = self.my_player.get_weapon()
        # deciding to pick up item
        try:
            pos_with_items = self.find_positions_with_items_in_range(self.curr_pos, 10)
            self.logger.info(f"number of item drops i see is {len(pos_with_items)}")

            # if weapon has better attack
            for pos in pos_with_items:
                items = self.game_state.get_board(self.curr_pos.get_board_id()).get_tile_at(pos).get_items()
                for item in items:
                    self.logger.info(f"I can seee an item {item}")
                    if isinstance(item, Weapon):
                        if item.get_attack() > weapon.get_attack():
                            if pos.get_x() == self.curr_pos.get_x() and pos.get_y() == self.curr_pos.get_y():
                                self.logger.info(f"Standing on weapon with attack {item.get_attack()}, picking up")
                                self.memory.set_value("last_action", "PICKUP")
                                return CharacterDecision(
                                    decision_type="PICKUP",
                                    action_position=None,
                                    action_index=0
                                )
                            else:
                                self.logger.info(f"Found weapon with attack {item.get_attack()}, approaching")
                                self.memory.set_value("last_action", "MOVE")
                                return CharacterDecision(
                                    decision_type="MOVE",
                                    action_position=self.find_position_to_move(self.my_player, pos),
                                    action_index=0
                                )
        except Exception as e:
            self.logger.warn(str(e))

        monster_list = self.crappy_find_enemies_by_distance(self.curr_pos, name_filter="slime")
        close_mon = monster_list[0]
        dist = self.curr_pos.manhattan_distance(close_mon.get_position())
        self.logger.warn("Closest monster is %s at %d" % (close_mon.get_name(), dist))

        decision = None


        self.logger.warn("Weapon range: %d, attack %d" % (weapon.get_range(), weapon.get_attack()))

        if(dist > weapon.get_range()):
            new_pos = self.find_position_to_move(self.my_player, close_mon.get_position())
            self.memory.set_value("last_action", "MOVE")
            decision = CharacterDecision(
                decision_type="MOVE",
                action_position=new_pos,
                action_index=0
            )
            self.logger.warn("Moving from (%d %d) => (%d %d)" % (self.curr_pos.x, self.curr_pos.y, new_pos.x, new_pos.y))
        else:
            self.memory.set_value("last_action", "ATTACK")
            decision = CharacterDecision(
                decision_type="ATTACK",
                action_position=close_mon.get_position(),
                action_index=0
            )
            self.logger.warn("Attacking %s" % close_mon.get_name())

        return decision

    def find_positions_with_items_in_range(self, pos, ran):
        positions = []
        for i in range(-ran, ran+1):
            for j in range(-ran, ran+1):
                position = pos.create(pos.get_x() + i, pos.get_y() + j, pos.get_board_id())
                if len(self.game_state.get_board(pos.get_board_id()).get_tile_at(position).get_items()) > 0:
                    positions.append(position)
        return positions

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
        try:
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
        except Exception as e:
            self.logger.warn(str(e))
            self.logger.warn("find position failed, defaulting to crappy find_position")
            return self.crappy_find_position_to_move(player, destination)
