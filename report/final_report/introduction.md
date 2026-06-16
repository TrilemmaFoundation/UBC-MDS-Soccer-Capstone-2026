# Background

The Trilemma Foundation aims to bring data-driven methods to football analysis. StatsBomb open data [@statsbomb2024] provides one of the richest publicly available sources of match event data, covering player-level on-ball actions (shots, passes, carries, pressures, dribbles, and more) at sub-second granularity. Despite its depth, the dataset is difficult to work with at scale. Event records are deeply nested JSON, competitions and seasons are fragmented across many files, and extracting meaningful player metrics requires complex aggregation logic that is impractical to write ad hoc.

# The Problem

No systematic, production-grade pipeline existed to transform StatsBomb event data into a unified analytical layer accessible to non-technical users. Analysts who could not write SQL against nested schemas were effectively locked out of the data. Trilemma needed a product that could answer tactical questions (which players fit a pressing role, which players perform differently for their country than their club) without requiring custom queries for every request.

# Refined Scientific Objectives

Over the course of the project, the initial problem was refined into three concrete and measurable research questions:

1. **RQ1 (Player archetypes):** What tactical archetypes exist across European football, and how does role distribution differ by position and competition?
2. **RQ2 (Cross-context consistency):** Do players maintain similar tactical profiles when playing for their club versus their national team, and which players specialize in one context?
3. **RQ3 (Natural language access):** Can a non-technical analyst query the full dataset in plain English and receive accurate, data-grounded answers in near real time?

These objectives were chosen because they are directly actionable for a football analytics organization. Archetype labelling supports scouting and squad-building decisions, consistency scoring informs national team selection strategy, and the chatbot removes the SQL barrier for day-to-day analytical work.

The data product addresses all three. The Looker Studio dashboard visualizes RQ1 and RQ2 findings interactively, and the chatbot covers RQ3 while also enabling ad-hoc queries against the full mart layer.
