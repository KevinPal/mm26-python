import logging

from mech.mania.starter_pack.domain.model.characters.character_decision import CharacterDecision
from mech.mania.starter_pack.domain.model.characters.position import Position
from mech.mania.starter_pack.domain.model.characters.player import Player
from mech.mania.starter_pack.domain.model.game_state import GameState
from mech.mania.starter_pack.domain.api import API

from mech.mania.starter_pack.domain.model.items.accessory import Accessory
from mech.mania.starter_pack.domain.model.items.clothes import Clothes
from mech.mania.starter_pack.domain.model.items.consumable import Consumable
from mech.mania.starter_pack.domain.model.items.hat import Hat
from mech.mania.starter_pack.domain.model.items.shoes import Shoes
from mech.mania.starter_pack.domain.model.items.weapon import Weapon


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
        self.game_state = game_state

        self.logger.info("In make_decision")
        self.logger.info(f"Currently at position: ({self.curr_pos.x},{self.curr_pos.y}) on board '{self.curr_pos.board_id}'")

        last_action, type = self.memory.get_value("last_action", str)
        try:
            last_index, type = self.memory.get_value("last_index", str)
            last_index = int(last_index)

            # print the player's inventory
            self.logger.info(f"Player has {len(self.my_player.get_inventory())} items")
            for item in self.my_player.get_inventory():
                self.logger.warn(self.print_item(item))

            # After pickup, equip the item
            if last_action is not None and last_action == "PICKUP":
                self.logger.info(f"Last action was picking up, equipping picked up object at index {last_index}")
                self.memory.set_value("last_action", "EQUIP")
                return CharacterDecision(
                    decision_type="EQUIP",
                    action_position=None,
                    action_index=last_index
                )
            # Drop old object
            if last_action is not None and last_action == "EQUIP":
                self.logger.info(f"Last action was equip, Dropping picked up object at index {last_index}")
                self.memory.set_value("last_action", "DROP")
                return CharacterDecision(
                    decision_type="DROP",
                    action_position=None,
                    action_index=last_index
                )

            # deciding to pick up item
            decision = self.scan_for_loot()
            if decision is not None:
                return decision
        except Exception as e:
            self.logger.warn(f"Error in mem parse {str(e)}")

        monster_list = self.crappy_find_enemies_by_distance(self.curr_pos, name_filter="slime")
        close_mon = monster_list[0]
        dist = self.curr_pos.manhattan_distance(close_mon.get_position())
        self.logger.warn("Closest monster is %s at %d" % (close_mon.get_name(), dist))

        decision = None

        weapon = self.my_player.get_weapon()

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

    def scan_for_loot(self):
        weapon = self.my_player.get_weapon()
        pos_with_items = self.find_positions_with_items_in_range(self.curr_pos, 10)
        self.logger.info(f"number of item drops i see is {len(pos_with_items)}")

        # if weapon has better attack
        for pos in pos_with_items:
            items = self.game_state.get_board(self.curr_pos.get_board_id()).get_tile_at(pos).get_items()
            for tile_item_index, item in enumerate(items):
                self.logger.info(f"I can seee an item {self.print_item(item)}")
                if isinstance(item, Weapon):
                    if item.get_attack() > weapon.get_attack():
                        return self.move_pickup(
                            pos,
                            tile_item_index,
                            f"Found weapon with attack {item.get_attack}",
                            f"Standing on weapon with attack {item.get_attack()}, picking up"
                        )
                else:
                    try:
                        my_obj = None

                        if isinstance(item, Hat):
                            my_obj = self.my_player.get_hat()
                        elif isinstance(item, Accessory):
                            my_obj = self.my_player.get_accessory()
                        elif isinstance(item, Clothes):
                            my_obj = self.my_player.get_clothes()
                        elif isinstance(item, Shoes):
                            my_obj = self.my_player.get_shoes()

                        if my_obj is None:
                            self.logger.warn(f"Item was unknown type: {str(type(item))}")
                            continue
                    except Exception as e:
                        self.logger.warn(f"Error in parsing item type: {str(e)}")
                        continue

                    try:
                        # List of stats to care about in order
                        functions = ["get_flat_experience_change",
                                     "get_percent_experience_change",
                                     "get_flat_attack_change",
                                     "get_percent_attack_change",
                                     "get_flat_speed_change",
                                     "get_percent_speed_change",
                                     "get_flat_health_change",
                                     "get_percent_health_change",
                                     "get_flat_defense_change",
                                     "get_percent_defense_change",
                                     "get_flat_regen_per_turn"]

                        should_take = None
                        working_func = ""
                        for foo in functions:
                            # Check if we care about our thing more
                            try:
                                my_func = getattr(my_obj.get_stats(), foo)
                                other_func = getattr(item.get_stats(), foo)
                            except Exception as e:
                                if foo in str(e):
                                    self.logger.warn(f"Skipping due to no {foo}")
                                    continue
                                else:
                                    raise e

                            # Ours is better, dont take
                            if (my_func() > other_func()):
                                should_take = False
                                self.logger.warn(f"Rejecting due to worse {foo}")
                                break
                            elif (my_func() == other_func()):
                                # Same stat, keep checking
                                continue
                            else:
                                # This is better, take it
                                should_take = True
                                working_func = foo
                                break

                        if should_take:
                            self.logger.info(f"Picking up {self.print_item(item)}, had {self.print_item(my_obj)}")
                            return self.move_pickup(
                                pos,
                                tile_item_index,
                                f"Found {str(type(item))}, picking due to {working_func}",
                                f"Picking up {str(type(item))}, picking due to {working_func}"
                            )
                    except Exception as e:
                        self.logger.warn(f"Error in comparing items: {str(e)}")
                        return None
        return None

    def move_pickup(self, pos, tile_item_index, approach_log="", pick_log=""):
        if pos.get_x() == self.curr_pos.get_x() and pos.get_y() == self.curr_pos.get_y():
            # self.logger.info()
            self.logger.info(pick_log)
            self.memory.set_value("last_action", "PICKUP")
            inv_index = len(self.my_player.get_inventory())
            self.memory.set_value("last_index", str(inv_index))
            self.logger.warn(f"Setting index to {inv_index}")
            return CharacterDecision(
                decision_type="PICKUP",
                action_position=None,
                action_index=tile_item_index
            )
        else:
            # self.logger.info()}, approaching")
            self.logger.info(approach_log)
            self.memory.set_value("last_action", "MOVE")
            return CharacterDecision(
                decision_type="MOVE",
                action_position=self.find_position_to_move(self.my_player, pos),
                action_index=0
            )

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

    def print_item(self, item):
        try:
            if isinstance(item, Weapon):
                return f"""
                    Weapon:
                    range:         {item.get_range()}
                    splash_radius: {item.get_splash_radius()}
                    on_hit_effect: {item.get_on_hit_effect()}
                    attack:        {item.get_attack()}
                """
            elif isinstance(item, Accessory):
                return f"""
                    Accessory:
                    magical_effect: {item.get_magic_effect()}
                """
            elif isinstance(item, Clothes):
                return f"""
                    Clothes:
                    stats: {item.get_stats()}
                """
            elif isinstance(item, Shoes):
                return f"""
                    Shoes:
                    stats: {item.get_stats()}
                """
            elif isinstance(item, Consumable):
                return f"""
                    Consumable:
                    stacks:  {item.get_stacks()}
                    effects: {item.get_effects()}
                """
            elif isinstance(item, Hat):
                return f"""
                    Hat:
                    magical_hat_effects: {item.magic_hat_effect()}:
                    stats:               {item.get_stats()}
                """
        except Exception as e:
            self.logger.warn(str(e))
            return str(item)
