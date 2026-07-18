extends Node

func choose_enemy_action(enemy_health: int) -> String:
	return "retreat" if enemy_health <= 0 else "attack"

