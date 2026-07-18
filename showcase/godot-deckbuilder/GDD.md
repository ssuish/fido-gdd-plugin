# Showcase deck-builder

[entity: class] DeckBuilder — owns one deterministic encounter.
[entity: function] draw_card — moves next card into hand.
[entity: function] resolve_enemy_turn — enemy acts after player turn.
[entity: card] Shield — deliberately missing implementation.
[entity: system] Enemy AI — rename candidate for `ai_controller.gd`.
[entity: state] FutureRelic [planned] — outside showcase slice.

## Visitor walkthrough

The visitor plays Strike and Block cards, then opens the finding evidence panel.
