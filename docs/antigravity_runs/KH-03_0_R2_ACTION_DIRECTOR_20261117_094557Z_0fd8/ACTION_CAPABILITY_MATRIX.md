# ACTION CAPABILITY MATRIX — KH-03.0.R2

- Registry version: kh03.r2.action_registry.v1
- Action count: 29
- Canonical SHA-256: bed02363f29648f27f4da7ac312c0f96f6986048f5d4bec4588b988d0b6121c5
- Dispatch mode: Fail-closed 1:1 to packs/squire/roman_master/action_registry.js (ROMAN_ACTION_RENDERERS). Zero default/guard fallback.

| action_id | domain | event_class | renderer_action_id | motion_profile_id | required_props | required_locations | required_pre_states | allowed_state_deltas |
|---|---|---|---|---|---|---|---|---|
| actor.idle_micro_act | ACTOR | reaction | actor_idle_micro_act | micro_breathe_blink | [] | [] | {} | {'actor_posture': 'idle_alert'} |
| actor.walk_stride | ACTOR | action | actor_walk_stride | biped_walk_cycle | [] | [] | {} | {'actor_gait': 'walk'} |
| actor.deadpan_walk_unaffected | ACTOR | reveal | actor_deadpan_walk_unaffected | deadpan_centurion_stride | ['roman_loaf'] | ['roman_market_hill'] | {'loaf_on_helmet': True} | {'centurion_composure': 'deadpan_steady', 'loaf_on_helmet': True} |
| actor.sprint_chase | ACTOR | action | actor_sprint_chase | biped_sprint_lean | [] | [] | {} | {'actor_gait': 'sprint'} |
| actor.reach_grab_prop | ACTOR | action | actor_reach_grab_prop | ik_reach_hand_lock | [] | [] | {} | {'hand_prop_contact': True} |
| actor.stop_brace | ACTOR | action | actor_stop_brace | rear_heel_brace_ik | ['hemp_rope', 'stone_bollard'] | [] | {} | {'actor_posture': 'braced_load', 'rope_taut': True} |
| actor.release_throw_prop | ACTOR | action | actor_release_throw_prop | overarm_throw_followthrough | [] | [] | {} | {'prop_airborne': True} |
| actor.point_shout_look | ACTOR | reaction | actor_point_shout_look | head_turn_arm_point | [] | [] | {} | {'actor_attention': 'alert_directed'} |
| actor.pickup_prop | ACTOR | action | actor_pickup_prop | stoop_pickup_ik | [] | [] | {} | {'prop_recovered': True} |
| actor.pull_drag_rope_tension | ACTOR | action | actor_pull_drag_rope_tension | two_hand_rope_haul | ['hemp_rope'] | [] | {} | {'rope_taut': True, 'prop_hauled': True} |
| actor.push_hold_load | ACTOR | action | actor_push_hold_load | forward_shoulder_push | [] | [] | {} | {'load_held': True} |
| actor.handoff_prop | ACTOR | action | actor_handoff_prop | two_actor_handoff_sync | [] | [] | {} | {'prop_handed_off': True} |
| actor.stumble_recover | ACTOR | action | actor_stumble_recover | forward_trip_recovery | [] | [] | {} | {'actor_balance': 'stumbled_recovered'} |
| actor.crowd_reaction_cheer | ACTOR | reaction | actor_crowd_reaction_cheer | multi_citizen_cheer_jump | [] | ['roman_market_hill'] | {'cart_stopped': True} | {'crowd_mood': 'cheering'} |
| prop.peg_crack_snap | PROP | insert | prop_peg_crack_snap | brittle_fracture_creep | ['brake_peg', 'market_cart'] | ['roman_market_hill'] | {} | {'peg_snapped': True, 'cart_rolling': True} |
| prop.cart_roll_slope | PROP | action | prop_cart_roll_slope | slope_accel_wheel_spin | ['market_cart'] | ['roman_market_hill'] | {'peg_snapped': True} | {'cart_rolling': True} |
| prop.rope_taut_post_wrap | PROP | insert | prop_rope_taut_post_wrap | catenary_to_chord_tension | ['hemp_rope', 'market_cart', 'stone_bollard'] | ['roman_market_hill'] | {} | {'rope_attached': True, 'rope_taut': True} |
| prop.cart_halt_skid | PROP | action | prop_cart_halt_skid | recoil_wheel_skid_halt | ['market_cart', 'bakery_oven', 'hemp_rope', 'stone_bollard'] | ['roman_market_hill'] | {'rope_taut': True} | {'cart_rolling': False, 'cart_stopped': True, 'jolt_occurred': True} |
| prop.prop_bounce_tray | PROP | insert | prop_bounce_tray | tray_impulse_launch | ['bread_tray', 'roman_loaf'] | ['roman_market_hill'] | {'cart_stopped': True} | {'loaf_airborne': True} |
| prop.prop_parabolic_arc | PROP | insert | prop_parabolic_arc | ballistic_parabolic_arc | ['roman_loaf'] | [] | {} | {'loaf_airborne': True} |
| prop.helmet_impact_settle | PROP | reveal | prop_helmet_impact_settle | soft_crust_helmet_squish | ['roman_loaf'] | ['roman_market_hill'] | {'loaf_airborne': True} | {'loaf_airborne': False, 'loaf_on_helmet': True} |
| prop.vexillum_river_drift | PROP | action | prop_vexillum_river_drift | water_current_bob_drift | ['cloth_vexillum', 'hemp_rope'] | ['roman_river_harbor'] | {} | {'vexillum_drifting': True} |
| prop.helmet_roll_under_bench | PROP | insert | prop_helmet_roll_under_bench | bronze_helmet_roll_decay | ['ceremonial_helmet', 'stone_bench'] | ['roman_forum_courtyard'] | {} | {'helmet_under_bench': True} |
| prop.scroll_open_adapter | PROP | reveal | prop_scroll_open_adapter | r1_scroll_unfurl | ['sealed_scroll'] | [] | {} | {'scroll_open': True} |
| prop.door_close_adapter | PROP | action | prop_door_close_adapter | r1_gate_slam_lock | ['city_gate'] | [] | {} | {'gate_closed': True} |
| world.market_hill_establish | WORLD | establish | world_market_hill_establish | slope_cart_and_glow_establish | ['bakery_oven', 'market_cart'] | ['roman_market_hill'] | {} | {'geography_established': True} |
| world.market_crowd_pass | WORLD | action | world_market_crowd_pass | foreground_parallax_pass | [] | ['roman_market_hill'] | {} | {'crowd_active': True} |
| world.river_harbor_establish | WORLD | establish | world_river_harbor_establish | river_current_ambience | [] | ['roman_river_harbor'] | {} | {'harbor_established': True} |
| world.forum_courtyard_establish | WORLD | establish | world_forum_courtyard_establish | courtyard_establish | ['stone_bench'] | ['roman_forum_courtyard'] | {} | {'forum_established': True} |
