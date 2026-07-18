class_name DeckBuilder
extends Node

signal state_changed(state: String)

@export var starting_energy: int = 3
@export var enemy_starting_health: int = 6
@export var player_starting_health: int = 6

var deck: Array[String] = ["strike", "block"]
var hand: Array[String] = []
var energy: int = 0
var enemy_health: int = 0
var player_health: int = 0
var player_block: int = 0
var state: String = "READY"

func reset_encounter() -> void:
	deck = ["strike", "block"]
	hand = []
	energy = starting_energy
	enemy_health = enemy_starting_health
	player_health = player_starting_health
	player_block = 0
	state = "PLAYER_TURN"
	draw_card()
	state_changed.emit(state)

func draw_card() -> String:
	if deck.is_empty():
		return ""
	var card: String = deck.pop_front()
	hand.append(card)
	return card

func play_strike() -> String:
	if state != "PLAYER_TURN" or energy < 1 or not hand.has("strike"):
		return "INVALID"
	hand.erase("strike")
	energy -= 1
	enemy_health -= 3
	return "STRIKE"

func play_block() -> String:
	if state != "PLAYER_TURN" or energy < 1 or not hand.has("block"):
		return "INVALID"
	hand.erase("block")
	energy -= 1
	player_block += 2
	return "BLOCK"

func resolve_enemy_turn() -> int:
	state = "ENEMY_TURN"
	var damage: int = maxi(0, 2 - player_block)
	player_block = 0
	player_health -= damage
	state = "VICTORY" if enemy_health <= 0 else "DEFEAT" if player_health <= 0 else "PLAYER_TURN"
	state_changed.emit(state)
	return damage
