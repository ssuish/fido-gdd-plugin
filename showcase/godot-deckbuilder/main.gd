extends Node

@onready var encounter: DeckBuilder = $DeckBuilder
@onready var status_label: Label = $UI/Status

func _ready() -> void:
	encounter.reset_encounter()
	encounter.state_changed.connect(_refresh_status)
	$UI/Strike.pressed.connect(_on_strike_pressed)
	$UI/Block.pressed.connect(_on_block_pressed)
	$UI/EndTurn.pressed.connect(_on_end_turn_pressed)
	_refresh_status(encounter.state)

func _on_strike_pressed() -> void:
	encounter.play_strike()
	_refresh_status(encounter.state)

func _on_block_pressed() -> void:
	encounter.play_block()
	_refresh_status(encounter.state)

func _on_end_turn_pressed() -> void:
	encounter.resolve_enemy_turn()

func _refresh_status(next_state: String) -> void:
	status_label.text = "%s | HP %d | Enemy %d | Energy %d" % [
		next_state,
		encounter.player_health,
		encounter.enemy_health,
		encounter.energy,
	]
