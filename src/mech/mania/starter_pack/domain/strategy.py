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
 e           )

    # feel free to write as many helper functions as you need!
    def find_position_to_move(self, player: Position, destination: Position) -> Position:
        path = self.api.find_path(player.get_position(), destination)
        pos = None
        if len(path) < player.get_speed():
            pos = path[-1]
        else:
            pos = path[player.get_speed() - 1]
        return pos
