from prefab_ui.components import Card, Text, Group, Badge, Grid
import json

card = Card(
    title="Test Card",
    subtitle="Subtitle",
    children=[
        Group(title="Group 1", children=[
            Grid(columns=2, children=[
                Text("Text 1"),
                Badge("Status", color="green")
            ])
        ])
    ]
)

print(json.dumps(card.to_dict() if hasattr(card, "to_dict") else card.__dict__, indent=2))
