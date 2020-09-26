import logging

from mech.mania.starter_pack.domain.model.characters.character_decision import CharacterDecision
from mech.mania.starter_pack.domain.model.characters.position import Position
from mech.mania.starter_pack.domain.model.game_state import GameState
from mech.mania.starter_pack.domain.api import API


class Strategy:
    def __init__(self, memory):
        self.memory = memory
        self.logger = logging.getLogger('strategy')
        self.logger.setLevel(logging.DEBUG)
        logging.basicConfig(level=logging.INFO)

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

        self.logger.info("In make_decision")

        #last_action, type = self.memory.get_value("last_action", str)
        #if last_action is not None and last_action == "PICKUP":
        #    self.logger.info("EQUIP")
        #    self.memory.set_value("last_action", "EQUIP")
        #    return CharacterDecision(
        #        decision_type="EQUIP",
        #        action_position=None,
        #        action_index=self.my_player.get_free_inventory_index()
        #    )

        #tile_items = self.board.get_tile_at(self.curr_pos).items
        #if tile_items is not None or len(tile_items) > 0:
        #    self.logger.info("PICKUP")
        #    self.memory.set_value("last_action", "PICKUP")
        #    return CharacterDecision(
        #        decision_type="PICKUP",
        #        action_position=None,
        #        action_index=0
        #    )

        weapon = self.my_player.get_weapon()
        enemies = self.api.find_enemies_by_distance(self.curr_pos)

        # if no enemies, sprint to portal
        if enemies is None or len(enemies) == 0:
            self.logger.info("There are no enemies")
            portal = self.api.find_closest_portal(self.curr_pos)

            if portal == self.curr_pos:
                self.logger.info("AT PORTAL. TRAVELING")
                return CharacterDecision(
                    decision_type="PORTAL"
                )
            else:
                self.logger.info("SPRINTING TO PORTAL")
                return CharacterDecision(
                    decision_type="MOVE",
                    action_position=find_position_to_move(self.curr_pos, self.api.find_closest_portal(self.curr_pos)),
                    action_index=None
                )
        self.logger.info("There are enemies")
        enemy_pos = enemies[0].get_position()
        if self.curr_pos.manhattan_distance(enemy_pos) <= weapon.get_range():
            self.logger.info("Hit enemy.")
            self.memory.set_value("last_action", "ATTACK")
            return CharacterDecision(
                decision_type="ATTACK",
                action_position=enemy_pos,
                action_index=None
            )
        else:
            self.logger.info("run to enemy.")
            self.memory.set_value("last_action", "MOVE")
            return CharacterDecision(
                decision_type="MOVE",
                action_position=find_position_to_move(self.my_player, enemy_pos),
                action_index=None
            )


    # feel free to write as many helper functions as you need!
    def find_position_to_move(self, player: Position, destination: Position) -> Position:
        path = self.api.find_path(player.get_position(), destination)
        pos = None
        if len(path) < player.get_speed():
            pos = path[-1]
        else:
            pos = path[player.get_speed() - 1]
        return pos
