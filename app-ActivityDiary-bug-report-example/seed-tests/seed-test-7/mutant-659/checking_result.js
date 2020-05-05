let checking_result = {
  "seed_test_id": "seed-test-7",
  "mutant_test_id": "mutant-659",
  "crash_error": false,
  "semantic_error": true,
  "insert_position": 3,
  "is_faithfully_replayed": false,
  "is_fully_replayed": true,
  "oracle_checking_batch_cnt": 16,
  "unreplayable_utg_event_ids_prefix": [],
  "number_of_unmatched_views": 83,
  "unmatched_views_of_seed_test": [
    {
      "checking_batch_id": 1,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 0,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_1.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": "<No Activity>",
        "view_str": "be35c96fb853b7d210ee0f7aa9e4e87d_0"
      },
      "to_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "c632488c24885f5aecd382121c4665f9_0"
      }
    },
    {
      "checking_batch_id": 1,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 0,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_1.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "-",
        "view_str": "9435f7ff11de0e81d4cff58f20a738ab_3"
      },
      "to_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "Sat, 2.22.20: 0 sec",
        "view_str": "0ceaa09eadcfc7516062b515e020dcb0_3"
      }
    },
    {
      "checking_batch_id": 1,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 0,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_1.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "22dc0dcd8c3f0fd0bf72933c2f46f9b4_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 08: 0 sec",
        "view_str": "e07c55445936460eaf9f5bcb7c7f3985_4"
      }
    },
    {
      "checking_batch_id": 1,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 0,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_1.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "68cffdd603039b5e40b36ee4bdb7fd0b_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "February 2020: 0 sec",
        "view_str": "31d72e2bc184772b790a8d8279efedc6_5"
      }
    },
    {
      "checking_batch_id": 1,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 0,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_1.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 44,
        "class": "android.widget.FrameLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/select_card_view",
        "text": null,
        "view_str": "d73ceb5e83557975823801abeba8c084_0"
      }
    },
    {
      "checking_batch_id": 1,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 0,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_1.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 45,
        "class": "android.widget.RelativeLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_background",
        "text": null,
        "view_str": "482553eeb495e54b173bb07b44b34386_0"
      }
    },
    {
      "checking_batch_id": 1,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 0,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_1.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 46,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "948db614d27c483c30da28d9a7f9d4b0_0"
      }
    },
    {
      "checking_batch_id": 2,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 0,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_2.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": "<No Activity>",
        "view_str": "be35c96fb853b7d210ee0f7aa9e4e87d_0"
      },
      "to_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "c632488c24885f5aecd382121c4665f9_0"
      }
    },
    {
      "checking_batch_id": 2,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 0,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_2.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "-",
        "view_str": "9435f7ff11de0e81d4cff58f20a738ab_3"
      },
      "to_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "Sat, 2.22.20: 16 sec",
        "view_str": "f0e0ed454b0a45a594888bede942ba22_3"
      }
    },
    {
      "checking_batch_id": 2,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 0,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_2.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "22dc0dcd8c3f0fd0bf72933c2f46f9b4_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 08: 16 sec",
        "view_str": "baf4b6d2bfdc45612ca6a6750e883fcd_4"
      }
    },
    {
      "checking_batch_id": 2,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 0,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_2.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "68cffdd603039b5e40b36ee4bdb7fd0b_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "February 2020: 16 sec",
        "view_str": "6ade2e501861f331abcf8d9e4e1ee271_5"
      }
    },
    {
      "checking_batch_id": 2,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 0,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_2.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 44,
        "class": "android.widget.FrameLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/select_card_view",
        "text": null,
        "view_str": "d73ceb5e83557975823801abeba8c084_0"
      }
    },
    {
      "checking_batch_id": 2,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 0,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_2.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 45,
        "class": "android.widget.RelativeLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_background",
        "text": null,
        "view_str": "482553eeb495e54b173bb07b44b34386_0"
      }
    },
    {
      "checking_batch_id": 2,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 0,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_2.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 46,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "948db614d27c483c30da28d9a7f9d4b0_0"
      }
    },
    {
      "checking_batch_id": 3,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 1,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_3.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": "<No Activity>",
        "view_str": "be35c96fb853b7d210ee0f7aa9e4e87d_0"
      },
      "to_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "c632488c24885f5aecd382121c4665f9_0"
      }
    },
    {
      "checking_batch_id": 3,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 1,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_3.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "-",
        "view_str": "9435f7ff11de0e81d4cff58f20a738ab_3"
      },
      "to_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "Sat, 2.22.20: 0 sec",
        "view_str": "0ceaa09eadcfc7516062b515e020dcb0_3"
      }
    },
    {
      "checking_batch_id": 3,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 1,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_3.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "22dc0dcd8c3f0fd0bf72933c2f46f9b4_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 08: 0 sec",
        "view_str": "e07c55445936460eaf9f5bcb7c7f3985_4"
      }
    },
    {
      "checking_batch_id": 3,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 1,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_3.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "68cffdd603039b5e40b36ee4bdb7fd0b_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "February 2020: 0 sec",
        "view_str": "31d72e2bc184772b790a8d8279efedc6_5"
      }
    },
    {
      "checking_batch_id": 3,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 1,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_3.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 44,
        "class": "android.widget.FrameLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/select_card_view",
        "text": null,
        "view_str": "d73ceb5e83557975823801abeba8c084_0"
      }
    },
    {
      "checking_batch_id": 3,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 1,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_3.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 45,
        "class": "android.widget.RelativeLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_background",
        "text": null,
        "view_str": "482553eeb495e54b173bb07b44b34386_0"
      }
    },
    {
      "checking_batch_id": 3,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 1,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_3.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 46,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "948db614d27c483c30da28d9a7f9d4b0_0"
      }
    },
    {
      "checking_batch_id": 4,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 1,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_4.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": "<No Activity>",
        "view_str": "be35c96fb853b7d210ee0f7aa9e4e87d_0"
      },
      "to_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "c632488c24885f5aecd382121c4665f9_0"
      }
    },
    {
      "checking_batch_id": 4,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 1,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_4.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "-",
        "view_str": "9435f7ff11de0e81d4cff58f20a738ab_3"
      },
      "to_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "Sat, 2.22.20: 16 sec",
        "view_str": "f0e0ed454b0a45a594888bede942ba22_3"
      }
    },
    {
      "checking_batch_id": 4,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 1,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_4.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "22dc0dcd8c3f0fd0bf72933c2f46f9b4_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 08: 16 sec",
        "view_str": "baf4b6d2bfdc45612ca6a6750e883fcd_4"
      }
    },
    {
      "checking_batch_id": 4,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 1,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_4.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "68cffdd603039b5e40b36ee4bdb7fd0b_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "February 2020: 16 sec",
        "view_str": "6ade2e501861f331abcf8d9e4e1ee271_5"
      }
    },
    {
      "checking_batch_id": 4,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 1,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_4.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 44,
        "class": "android.widget.FrameLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/select_card_view",
        "text": null,
        "view_str": "d73ceb5e83557975823801abeba8c084_0"
      }
    },
    {
      "checking_batch_id": 4,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 1,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_4.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 45,
        "class": "android.widget.RelativeLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_background",
        "text": null,
        "view_str": "482553eeb495e54b173bb07b44b34386_0"
      }
    },
    {
      "checking_batch_id": 4,
      "from_state_str": "64b4417cb88e1cacf8c1360b927dfdea",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 1,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000541-195.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_4.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 46,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "948db614d27c483c30da28d9a7f9d4b0_0"
      }
    },
    {
      "checking_batch_id": 5,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 2,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_5.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": "<No Activity>",
        "view_str": "be35c96fb853b7d210ee0f7aa9e4e87d_0"
      },
      "to_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "c632488c24885f5aecd382121c4665f9_0"
      }
    },
    {
      "checking_batch_id": 5,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 2,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_5.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "-",
        "view_str": "9435f7ff11de0e81d4cff58f20a738ab_3"
      },
      "to_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "Sat, 2.22.20: 0 sec",
        "view_str": "0ceaa09eadcfc7516062b515e020dcb0_3"
      }
    },
    {
      "checking_batch_id": 5,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 2,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_5.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "22dc0dcd8c3f0fd0bf72933c2f46f9b4_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 08: 0 sec",
        "view_str": "e07c55445936460eaf9f5bcb7c7f3985_4"
      }
    },
    {
      "checking_batch_id": 5,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 2,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_5.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "68cffdd603039b5e40b36ee4bdb7fd0b_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "February 2020: 0 sec",
        "view_str": "31d72e2bc184772b790a8d8279efedc6_5"
      }
    },
    {
      "checking_batch_id": 5,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 2,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_5.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 44,
        "class": "android.widget.FrameLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/select_card_view",
        "text": null,
        "view_str": "d73ceb5e83557975823801abeba8c084_0"
      }
    },
    {
      "checking_batch_id": 5,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 2,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_5.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 45,
        "class": "android.widget.RelativeLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_background",
        "text": null,
        "view_str": "482553eeb495e54b173bb07b44b34386_0"
      }
    },
    {
      "checking_batch_id": 5,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 2,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_5.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 46,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "948db614d27c483c30da28d9a7f9d4b0_0"
      }
    },
    {
      "checking_batch_id": 6,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 2,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_6.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": "<No Activity>",
        "view_str": "be35c96fb853b7d210ee0f7aa9e4e87d_0"
      },
      "to_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "c632488c24885f5aecd382121c4665f9_0"
      }
    },
    {
      "checking_batch_id": 6,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 2,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_6.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "-",
        "view_str": "9435f7ff11de0e81d4cff58f20a738ab_3"
      },
      "to_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "Sat, 2.22.20: 16 sec",
        "view_str": "f0e0ed454b0a45a594888bede942ba22_3"
      }
    },
    {
      "checking_batch_id": 6,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 2,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_6.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "22dc0dcd8c3f0fd0bf72933c2f46f9b4_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 08: 16 sec",
        "view_str": "baf4b6d2bfdc45612ca6a6750e883fcd_4"
      }
    },
    {
      "checking_batch_id": 6,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 2,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_6.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "68cffdd603039b5e40b36ee4bdb7fd0b_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "February 2020: 16 sec",
        "view_str": "6ade2e501861f331abcf8d9e4e1ee271_5"
      }
    },
    {
      "checking_batch_id": 6,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 2,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_6.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 44,
        "class": "android.widget.FrameLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/select_card_view",
        "text": null,
        "view_str": "d73ceb5e83557975823801abeba8c084_0"
      }
    },
    {
      "checking_batch_id": 6,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 2,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_6.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 45,
        "class": "android.widget.RelativeLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_background",
        "text": null,
        "view_str": "482553eeb495e54b173bb07b44b34386_0"
      }
    },
    {
      "checking_batch_id": 6,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 2,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_6.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 46,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "948db614d27c483c30da28d9a7f9d4b0_0"
      }
    },
    {
      "checking_batch_id": 7,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 3,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_7.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": "<No Activity>",
        "view_str": "be35c96fb853b7d210ee0f7aa9e4e87d_0"
      },
      "to_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "c632488c24885f5aecd382121c4665f9_0"
      }
    },
    {
      "checking_batch_id": 7,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 3,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_7.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "-",
        "view_str": "9435f7ff11de0e81d4cff58f20a738ab_3"
      },
      "to_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "Sat, 2.22.20: 0 sec",
        "view_str": "0ceaa09eadcfc7516062b515e020dcb0_3"
      }
    },
    {
      "checking_batch_id": 7,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 3,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_7.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "22dc0dcd8c3f0fd0bf72933c2f46f9b4_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 08: 0 sec",
        "view_str": "e07c55445936460eaf9f5bcb7c7f3985_4"
      }
    },
    {
      "checking_batch_id": 7,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 3,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_7.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "68cffdd603039b5e40b36ee4bdb7fd0b_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "February 2020: 0 sec",
        "view_str": "31d72e2bc184772b790a8d8279efedc6_5"
      }
    },
    {
      "checking_batch_id": 7,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 3,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_7.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 44,
        "class": "android.widget.FrameLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/select_card_view",
        "text": null,
        "view_str": "d73ceb5e83557975823801abeba8c084_0"
      }
    },
    {
      "checking_batch_id": 7,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 3,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_7.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 45,
        "class": "android.widget.RelativeLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_background",
        "text": null,
        "view_str": "482553eeb495e54b173bb07b44b34386_0"
      }
    },
    {
      "checking_batch_id": 7,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 3,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_7.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 46,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "948db614d27c483c30da28d9a7f9d4b0_0"
      }
    },
    {
      "checking_batch_id": 8,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 3,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_8.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": "<No Activity>",
        "view_str": "be35c96fb853b7d210ee0f7aa9e4e87d_0"
      },
      "to_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "c632488c24885f5aecd382121c4665f9_0"
      }
    },
    {
      "checking_batch_id": 8,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 3,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_8.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "-",
        "view_str": "9435f7ff11de0e81d4cff58f20a738ab_3"
      },
      "to_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "Sat, 2.22.20: 16 sec",
        "view_str": "f0e0ed454b0a45a594888bede942ba22_3"
      }
    },
    {
      "checking_batch_id": 8,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 3,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_8.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "22dc0dcd8c3f0fd0bf72933c2f46f9b4_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 08: 16 sec",
        "view_str": "baf4b6d2bfdc45612ca6a6750e883fcd_4"
      }
    },
    {
      "checking_batch_id": 8,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 3,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_8.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "68cffdd603039b5e40b36ee4bdb7fd0b_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "February 2020: 16 sec",
        "view_str": "6ade2e501861f331abcf8d9e4e1ee271_5"
      }
    },
    {
      "checking_batch_id": 8,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 3,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_8.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 44,
        "class": "android.widget.FrameLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/select_card_view",
        "text": null,
        "view_str": "d73ceb5e83557975823801abeba8c084_0"
      }
    },
    {
      "checking_batch_id": 8,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 3,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_8.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 45,
        "class": "android.widget.RelativeLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_background",
        "text": null,
        "view_str": "482553eeb495e54b173bb07b44b34386_0"
      }
    },
    {
      "checking_batch_id": 8,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 3,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_8.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 46,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "948db614d27c483c30da28d9a7f9d4b0_0"
      }
    },
    {
      "checking_batch_id": 9,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 4,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_9.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": "<No Activity>",
        "view_str": "be35c96fb853b7d210ee0f7aa9e4e87d_0"
      },
      "to_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "c632488c24885f5aecd382121c4665f9_0"
      }
    },
    {
      "checking_batch_id": 9,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 4,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_9.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "-",
        "view_str": "9435f7ff11de0e81d4cff58f20a738ab_3"
      },
      "to_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "Sat, 2.22.20: 0 sec",
        "view_str": "0ceaa09eadcfc7516062b515e020dcb0_3"
      }
    },
    {
      "checking_batch_id": 9,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 4,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_9.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "22dc0dcd8c3f0fd0bf72933c2f46f9b4_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 08: 0 sec",
        "view_str": "e07c55445936460eaf9f5bcb7c7f3985_4"
      }
    },
    {
      "checking_batch_id": 9,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 4,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_9.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "68cffdd603039b5e40b36ee4bdb7fd0b_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "February 2020: 0 sec",
        "view_str": "31d72e2bc184772b790a8d8279efedc6_5"
      }
    },
    {
      "checking_batch_id": 9,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 4,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_9.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 44,
        "class": "android.widget.FrameLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/select_card_view",
        "text": null,
        "view_str": "d73ceb5e83557975823801abeba8c084_0"
      }
    },
    {
      "checking_batch_id": 9,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 4,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_9.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 45,
        "class": "android.widget.RelativeLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_background",
        "text": null,
        "view_str": "482553eeb495e54b173bb07b44b34386_0"
      }
    },
    {
      "checking_batch_id": 9,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "from_state_id": 4,
      "to_state_id": 6,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "annotated_utg_file": "utg_9.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 46,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "948db614d27c483c30da28d9a7f9d4b0_0"
      }
    },
    {
      "checking_batch_id": 10,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 4,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_10.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": "<No Activity>",
        "view_str": "be35c96fb853b7d210ee0f7aa9e4e87d_0"
      },
      "to_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "c632488c24885f5aecd382121c4665f9_0"
      }
    },
    {
      "checking_batch_id": 10,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 4,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_10.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "-",
        "view_str": "9435f7ff11de0e81d4cff58f20a738ab_3"
      },
      "to_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "Sat, 2.22.20: 16 sec",
        "view_str": "f0e0ed454b0a45a594888bede942ba22_3"
      }
    },
    {
      "checking_batch_id": 10,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 4,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_10.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "22dc0dcd8c3f0fd0bf72933c2f46f9b4_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 08: 16 sec",
        "view_str": "baf4b6d2bfdc45612ca6a6750e883fcd_4"
      }
    },
    {
      "checking_batch_id": 10,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 4,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_10.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "68cffdd603039b5e40b36ee4bdb7fd0b_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "February 2020: 16 sec",
        "view_str": "6ade2e501861f331abcf8d9e4e1ee271_5"
      }
    },
    {
      "checking_batch_id": 10,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 4,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_10.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 44,
        "class": "android.widget.FrameLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/select_card_view",
        "text": null,
        "view_str": "d73ceb5e83557975823801abeba8c084_0"
      }
    },
    {
      "checking_batch_id": 10,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 4,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_10.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 45,
        "class": "android.widget.RelativeLayout",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_background",
        "text": null,
        "view_str": "482553eeb495e54b173bb07b44b34386_0"
      }
    },
    {
      "checking_batch_id": 10,
      "from_state_str": "5eb9421c2c7507ccf93495d69425c73f",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 4,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000547-198.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_10.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 46,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": null,
        "view_str": "948db614d27c483c30da28d9a7f9d4b0_0"
      }
    },
    {
      "checking_batch_id": 11,
      "from_state_str": "1dacdc6fd3b1c4539eb196feedb2636c",
      "to_state_str": "a39e543aa0b29f6391bdd5841cdcb903",
      "from_state_id": 5,
      "to_state_id": 11,
      "from_state_json_file": "../../../states/state_2020-02-22_000600-204.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000625-216.json",
      "annotated_utg_file": "utg_11.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 8,
        "class": "android.widget.TextView",
        "resource_id": null,
        "text": "New activity",
        "view_str": "61fca05c20da1ebaf7b4d79847b44e8e_1"
      },
      "to_view": {
        "temp_id": 8,
        "class": "android.widget.TextView",
        "resource_id": null,
        "text": "Gardening",
        "view_str": "30ce36eae598ae4e7195f7b68d89acdd_1"
      }
    },
    {
      "checking_batch_id": 11,
      "from_state_str": "1dacdc6fd3b1c4539eb196feedb2636c",
      "to_state_str": "a39e543aa0b29f6391bdd5841cdcb903",
      "from_state_id": 5,
      "to_state_id": 11,
      "from_state_json_file": "../../../states/state_2020-02-22_000600-204.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000625-216.json",
      "annotated_utg_file": "utg_11.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 18,
        "class": "android.widget.EditText",
        "resource_id": "de.rampro.activitydiary.debug:id/edit_activity_name",
        "text": "Activity title",
        "view_str": "16e81780273a663b96a1f9ad1218cd58_0"
      },
      "to_view": {
        "temp_id": 18,
        "class": "android.widget.EditText",
        "resource_id": "de.rampro.activitydiary.debug:id/edit_activity_name",
        "text": "Gardening",
        "view_str": "969c788f9f2f2e02bc54d18a7581f38e_0"
      }
    },
    {
      "checking_batch_id": 12,
      "from_state_str": "1dacdc6fd3b1c4539eb196feedb2636c",
      "to_state_str": "abe23bda3bb47a08a9f98422006b9830",
      "from_state_id": 5,
      "to_state_id": 12,
      "from_state_json_file": "../../../states/state_2020-02-22_000600-204.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000629-218.json",
      "annotated_utg_file": "utg_12.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 8,
        "class": "android.widget.TextView",
        "resource_id": null,
        "text": "New activity",
        "view_str": "61fca05c20da1ebaf7b4d79847b44e8e_1"
      },
      "to_view": {
        "temp_id": 8,
        "class": "android.widget.TextView",
        "resource_id": null,
        "text": "Gardening",
        "view_str": "30ce36eae598ae4e7195f7b68d89acdd_1"
      }
    },
    {
      "checking_batch_id": 12,
      "from_state_str": "1dacdc6fd3b1c4539eb196feedb2636c",
      "to_state_str": "abe23bda3bb47a08a9f98422006b9830",
      "from_state_id": 5,
      "to_state_id": 12,
      "from_state_json_file": "../../../states/state_2020-02-22_000600-204.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000629-218.json",
      "annotated_utg_file": "utg_12.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 18,
        "class": "android.widget.EditText",
        "resource_id": "de.rampro.activitydiary.debug:id/edit_activity_name",
        "text": "Activity title",
        "view_str": "16e81780273a663b96a1f9ad1218cd58_0"
      },
      "to_view": {
        "temp_id": 18,
        "class": "android.widget.EditText",
        "resource_id": "de.rampro.activitydiary.debug:id/edit_activity_name",
        "text": "HelloWorld",
        "view_str": "a5dc1619cd1d5a94061c4b5bcefb54a9_0"
      }
    },
    {
      "checking_batch_id": 12,
      "from_state_str": "1dacdc6fd3b1c4539eb196feedb2636c",
      "to_state_str": "abe23bda3bb47a08a9f98422006b9830",
      "from_state_id": 5,
      "to_state_id": 12,
      "from_state_json_file": "../../../states/state_2020-02-22_000600-204.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000629-218.json",
      "annotated_utg_file": "utg_12.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 21,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/textinput_error",
        "text": "Activity with name  already exists",
        "view_str": "280cae95375286a955481dfb1823f18e_0"
      }
    },
    {
      "checking_batch_id": 13,
      "from_state_str": "1dacdc6fd3b1c4539eb196feedb2636c",
      "to_state_str": "7dd4e856859d8dc8b6bbf60503ec4816",
      "from_state_id": 5,
      "to_state_id": 13,
      "from_state_json_file": "../../../states/state_2020-02-22_000600-204.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000632-220.json",
      "annotated_utg_file": "utg_13.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 8,
        "class": "android.widget.TextView",
        "resource_id": null,
        "text": "New activity",
        "view_str": "61fca05c20da1ebaf7b4d79847b44e8e_1"
      },
      "to_view": {
        "temp_id": 8,
        "class": "android.widget.TextView",
        "resource_id": null,
        "text": "Gardening",
        "view_str": "30ce36eae598ae4e7195f7b68d89acdd_1"
      }
    },
    {
      "checking_batch_id": 13,
      "from_state_str": "1dacdc6fd3b1c4539eb196feedb2636c",
      "to_state_str": "7dd4e856859d8dc8b6bbf60503ec4816",
      "from_state_id": 5,
      "to_state_id": 13,
      "from_state_json_file": "../../../states/state_2020-02-22_000600-204.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000632-220.json",
      "annotated_utg_file": "utg_13.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 18,
        "class": "android.widget.EditText",
        "resource_id": "de.rampro.activitydiary.debug:id/edit_activity_name",
        "text": "Activity title",
        "view_str": "16e81780273a663b96a1f9ad1218cd58_0"
      },
      "to_view": {
        "temp_id": 18,
        "class": "android.widget.EditText",
        "resource_id": "de.rampro.activitydiary.debug:id/edit_activity_name",
        "text": "HelloWorld",
        "view_str": "a5dc1619cd1d5a94061c4b5bcefb54a9_0"
      }
    },
    {
      "checking_batch_id": 14,
      "from_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 6,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_14.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "Sat, 2.22.20: 0 sec",
        "view_str": "0ceaa09eadcfc7516062b515e020dcb0_3"
      },
      "to_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "Sat, 2.22.20: 16 sec",
        "view_str": "f0e0ed454b0a45a594888bede942ba22_3"
      }
    },
    {
      "checking_batch_id": 14,
      "from_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 6,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_14.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 08: 0 sec",
        "view_str": "e07c55445936460eaf9f5bcb7c7f3985_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 08: 16 sec",
        "view_str": "baf4b6d2bfdc45612ca6a6750e883fcd_4"
      }
    },
    {
      "checking_batch_id": 14,
      "from_state_str": "f9b5a5ef41502bcda39b40f8debf7b38",
      "to_state_str": "1d72826dc5929ab4a89e43ecbcbf03d3",
      "from_state_id": 6,
      "to_state_id": 10,
      "from_state_json_file": "../../../states/state_2020-02-22_000603-206.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000620-214.json",
      "annotated_utg_file": "utg_14.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "February 2020: 0 sec",
        "view_str": "31d72e2bc184772b790a8d8279efedc6_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "February 2020: 16 sec",
        "view_str": "6ade2e501861f331abcf8d9e4e1ee271_5"
      }
    },
    {
      "checking_batch_id": 15,
      "from_state_str": "a39e543aa0b29f6391bdd5841cdcb903",
      "to_state_str": "abe23bda3bb47a08a9f98422006b9830",
      "from_state_id": 11,
      "to_state_id": 12,
      "from_state_json_file": "../../../states/state_2020-02-22_000625-216.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000629-218.json",
      "annotated_utg_file": "utg_15.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 20,
        "class": "android.widget.FrameLayout",
        "resource_id": null,
        "text": null,
        "view_str": "0f384432d23073031a3e96748b587048_0"
      }
    },
    {
      "checking_batch_id": 15,
      "from_state_str": "a39e543aa0b29f6391bdd5841cdcb903",
      "to_state_str": "abe23bda3bb47a08a9f98422006b9830",
      "from_state_id": 11,
      "to_state_id": 12,
      "from_state_json_file": "../../../states/state_2020-02-22_000625-216.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000629-218.json",
      "annotated_utg_file": "utg_15.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 21,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/textinput_error",
        "text": "Activity with name  already exists",
        "view_str": "280cae95375286a955481dfb1823f18e_0"
      }
    },
    {
      "checking_batch_id": 16,
      "from_state_str": "abe23bda3bb47a08a9f98422006b9830",
      "to_state_str": "7dd4e856859d8dc8b6bbf60503ec4816",
      "from_state_id": 12,
      "to_state_id": 13,
      "from_state_json_file": "../../../states/state_2020-02-22_000629-218.json",
      "to_state_json_file": "../../../states/state_2020-02-22_000632-220.json",
      "annotated_utg_file": "utg_16.json",
      "operation": "DELETE",
      "from_view": {
        "temp_id": 21,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/textinput_error",
        "text": "Activity with name  already exists",
        "view_str": "280cae95375286a955481dfb1823f18e_0"
      },
      "to_view": null
    }
  ],
  "unmatched_views_of_mutant_test": [
    {
      "checking_batch_id": 1,
      "from_state_str": "1f81ce3419826244b4b3a649877e102a",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 0,
      "to_state_id": 8,
      "from_state_json_file": "states/state_2020-03-04_060545-0.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_1.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "0d2dc141b525e05f88becaadb6b675c5_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 10: 0 sec",
        "view_str": "1d04dada1fe398d339060251daf4fadc_4"
      }
    },
    {
      "checking_batch_id": 1,
      "from_state_str": "1f81ce3419826244b4b3a649877e102a",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 0,
      "to_state_id": 8,
      "from_state_json_file": "states/state_2020-03-04_060545-0.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_1.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "e624f7868ce0312c0e20743bfce4c18c_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "March 2020: 0 sec",
        "view_str": "c3a08668588d9e3249b5670e5d6e0d62_5"
      }
    },
    {
      "checking_batch_id": 2,
      "from_state_str": "1f81ce3419826244b4b3a649877e102a",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 0,
      "to_state_id": 12,
      "from_state_json_file": "states/state_2020-03-04_060545-0.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_2.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "0d2dc141b525e05f88becaadb6b675c5_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 10: 0 sec",
        "view_str": "1d04dada1fe398d339060251daf4fadc_4"
      }
    },
    {
      "checking_batch_id": 2,
      "from_state_str": "1f81ce3419826244b4b3a649877e102a",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 0,
      "to_state_id": 12,
      "from_state_json_file": "states/state_2020-03-04_060545-0.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_2.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "e624f7868ce0312c0e20743bfce4c18c_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "March 2020: 0 sec",
        "view_str": "c3a08668588d9e3249b5670e5d6e0d62_5"
      }
    },
    {
      "checking_batch_id": 3,
      "from_state_str": "1f81ce3419826244b4b3a649877e102a",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 1,
      "to_state_id": 8,
      "from_state_json_file": "states/state_2020-03-04_060545-0.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_3.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "0d2dc141b525e05f88becaadb6b675c5_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 10: 0 sec",
        "view_str": "1d04dada1fe398d339060251daf4fadc_4"
      }
    },
    {
      "checking_batch_id": 3,
      "from_state_str": "1f81ce3419826244b4b3a649877e102a",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 1,
      "to_state_id": 8,
      "from_state_json_file": "states/state_2020-03-04_060545-0.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_3.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "e624f7868ce0312c0e20743bfce4c18c_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "March 2020: 0 sec",
        "view_str": "c3a08668588d9e3249b5670e5d6e0d62_5"
      }
    },
    {
      "checking_batch_id": 4,
      "from_state_str": "1f81ce3419826244b4b3a649877e102a",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 1,
      "to_state_id": 12,
      "from_state_json_file": "states/state_2020-03-04_060545-0.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_4.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "0d2dc141b525e05f88becaadb6b675c5_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 10: 0 sec",
        "view_str": "1d04dada1fe398d339060251daf4fadc_4"
      }
    },
    {
      "checking_batch_id": 4,
      "from_state_str": "1f81ce3419826244b4b3a649877e102a",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 1,
      "to_state_id": 12,
      "from_state_json_file": "states/state_2020-03-04_060545-0.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_4.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "e624f7868ce0312c0e20743bfce4c18c_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "March 2020: 0 sec",
        "view_str": "c3a08668588d9e3249b5670e5d6e0d62_5"
      }
    },
    {
      "checking_batch_id": 5,
      "from_state_str": "1f81ce3419826244b4b3a649877e102a",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 2,
      "to_state_id": 8,
      "from_state_json_file": "states/state_2020-03-04_060545-0.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_5.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 37,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/duration_label",
        "text": "Since just now",
        "view_str": "f9d6d73313c8d003d275b61fbc64e7af_0"
      },
      "to_view": {
        "temp_id": 37,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/duration_label",
        "text": "Since a few seconds",
        "view_str": "33897b6b1688ce47f31a2d3e868b5b3d_0"
      }
    },
    {
      "checking_batch_id": 5,
      "from_state_str": "1f81ce3419826244b4b3a649877e102a",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 2,
      "to_state_id": 8,
      "from_state_json_file": "states/state_2020-03-04_060545-0.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_5.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "0d2dc141b525e05f88becaadb6b675c5_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 10: 0 sec",
        "view_str": "1d04dada1fe398d339060251daf4fadc_4"
      }
    },
    {
      "checking_batch_id": 5,
      "from_state_str": "1f81ce3419826244b4b3a649877e102a",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 2,
      "to_state_id": 8,
      "from_state_json_file": "states/state_2020-03-04_060545-0.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_5.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "e624f7868ce0312c0e20743bfce4c18c_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "March 2020: 0 sec",
        "view_str": "c3a08668588d9e3249b5670e5d6e0d62_5"
      }
    },
    {
      "checking_batch_id": 6,
      "from_state_str": "1f81ce3419826244b4b3a649877e102a",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 2,
      "to_state_id": 12,
      "from_state_json_file": "states/state_2020-03-04_060545-0.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_6.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 37,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/duration_label",
        "text": "Since just now",
        "view_str": "f9d6d73313c8d003d275b61fbc64e7af_0"
      },
      "to_view": {
        "temp_id": 37,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/duration_label",
        "text": "Since a few seconds",
        "view_str": "33897b6b1688ce47f31a2d3e868b5b3d_0"
      }
    },
    {
      "checking_batch_id": 6,
      "from_state_str": "1f81ce3419826244b4b3a649877e102a",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 2,
      "to_state_id": 12,
      "from_state_json_file": "states/state_2020-03-04_060545-0.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_6.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "0d2dc141b525e05f88becaadb6b675c5_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 10: 0 sec",
        "view_str": "1d04dada1fe398d339060251daf4fadc_4"
      }
    },
    {
      "checking_batch_id": 6,
      "from_state_str": "1f81ce3419826244b4b3a649877e102a",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 2,
      "to_state_id": 12,
      "from_state_json_file": "states/state_2020-03-04_060545-0.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_6.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "e624f7868ce0312c0e20743bfce4c18c_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "March 2020: 0 sec",
        "view_str": "c3a08668588d9e3249b5670e5d6e0d62_5"
      }
    },
    {
      "checking_batch_id": 7,
      "from_state_str": "4fdbde056421c19e1a4cc1865dc2e057",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 3,
      "to_state_id": 8,
      "from_state_json_file": "states/state_2020-03-04_060552-5.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_7.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "0d2dc141b525e05f88becaadb6b675c5_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 10: 0 sec",
        "view_str": "1d04dada1fe398d339060251daf4fadc_4"
      }
    },
    {
      "checking_batch_id": 7,
      "from_state_str": "4fdbde056421c19e1a4cc1865dc2e057",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 3,
      "to_state_id": 8,
      "from_state_json_file": "states/state_2020-03-04_060552-5.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_7.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "e624f7868ce0312c0e20743bfce4c18c_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "March 2020: 0 sec",
        "view_str": "c3a08668588d9e3249b5670e5d6e0d62_5"
      }
    },
    {
      "checking_batch_id": 8,
      "from_state_str": "4fdbde056421c19e1a4cc1865dc2e057",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 3,
      "to_state_id": 12,
      "from_state_json_file": "states/state_2020-03-04_060552-5.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_8.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": null,
        "view_str": "0d2dc141b525e05f88becaadb6b675c5_4"
      },
      "to_view": {
        "temp_id": 41,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_week_label",
        "text": "2020 Week 10: 0 sec",
        "view_str": "1d04dada1fe398d339060251daf4fadc_4"
      }
    },
    {
      "checking_batch_id": 8,
      "from_state_str": "4fdbde056421c19e1a4cc1865dc2e057",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 3,
      "to_state_id": 12,
      "from_state_json_file": "states/state_2020-03-04_060552-5.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_8.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": null,
        "view_str": "e624f7868ce0312c0e20743bfce4c18c_5"
      },
      "to_view": {
        "temp_id": 42,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_month_label",
        "text": "March 2020: 0 sec",
        "view_str": "c3a08668588d9e3249b5670e5d6e0d62_5"
      }
    },
    {
      "checking_batch_id": 9,
      "from_state_str": "ec5c0c7ad7a1c1176bda39f6c1b11615",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 6,
      "to_state_id": 8,
      "from_state_json_file": "states/state_2020-03-04_060557-9.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_9.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": "Gardening",
        "view_str": "fac6612414ec4a32c098d092afbdb426_0"
      },
      "to_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": "<No Activity>",
        "view_str": "b2fd192c7762e95394ef4246ca71e3f9_0"
      }
    },
    {
      "checking_batch_id": 9,
      "from_state_str": "ec5c0c7ad7a1c1176bda39f6c1b11615",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 6,
      "to_state_id": 8,
      "from_state_json_file": "states/state_2020-03-04_060557-9.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_9.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "Wed, 3.04.20: 0 sec",
        "view_str": "050777afe067cc686dfd148c97d56271_3"
      },
      "to_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "-",
        "view_str": "06e3e37c106202331d8728b228d9a820_3"
      }
    },
    {
      "checking_batch_id": 10,
      "from_state_str": "ec5c0c7ad7a1c1176bda39f6c1b11615",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 6,
      "to_state_id": 12,
      "from_state_json_file": "states/state_2020-03-04_060557-9.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_10.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": "Gardening",
        "view_str": "fac6612414ec4a32c098d092afbdb426_0"
      },
      "to_view": {
        "temp_id": 23,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/activity_name",
        "text": "<No Activity>",
        "view_str": "b2fd192c7762e95394ef4246ca71e3f9_0"
      }
    },
    {
      "checking_batch_id": 10,
      "from_state_str": "ec5c0c7ad7a1c1176bda39f6c1b11615",
      "to_state_str": "637649ba1bb086531aeae3b95e055d98",
      "from_state_id": 6,
      "to_state_id": 12,
      "from_state_json_file": "states/state_2020-03-04_060557-9.json",
      "to_state_json_file": "states/state_2020-03-04_060606-15.json",
      "annotated_utg_file": "utg_10.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "Wed, 3.04.20: 0 sec",
        "view_str": "050777afe067cc686dfd148c97d56271_3"
      },
      "to_view": {
        "temp_id": 40,
        "class": "android.widget.TextView",
        "resource_id": "de.rampro.activitydiary.debug:id/total_today_label",
        "text": "-",
        "view_str": "06e3e37c106202331d8728b228d9a820_3"
      }
    },
    {
      "checking_batch_id": 12,
      "from_state_str": "2fa893f5b725807bfef0dcc75b24865f",
      "to_state_str": "011da01f7d6fe08f48efd1716f14ac52",
      "from_state_id": 7,
      "to_state_id": 14,
      "from_state_json_file": "states/state_2020-03-04_060603-13.json",
      "to_state_json_file": "states/state_2020-03-04_060624-27.json",
      "annotated_utg_file": "utg_12.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 18,
        "class": "android.widget.EditText",
        "resource_id": "de.rampro.activitydiary.debug:id/edit_activity_name",
        "text": "Gardening",
        "view_str": "f425448d22b9eded95e32d4c297dd200_0"
      },
      "to_view": {
        "temp_id": 18,
        "class": "android.widget.EditText",
        "resource_id": "de.rampro.activitydiary.debug:id/edit_activity_name",
        "text": "HelloWorld",
        "view_str": "1e9669219eeb32fb34a2696309c4c552_0"
      }
    },
    {
      "checking_batch_id": 13,
      "from_state_str": "2fa893f5b725807bfef0dcc75b24865f",
      "to_state_str": "011da01f7d6fe08f48efd1716f14ac52",
      "from_state_id": 7,
      "to_state_id": 15,
      "from_state_json_file": "states/state_2020-03-04_060603-13.json",
      "to_state_json_file": "states/state_2020-03-04_060624-27.json",
      "annotated_utg_file": "utg_13.json",
      "operation": "CHANGE",
      "from_view": {
        "temp_id": 18,
        "class": "android.widget.EditText",
        "resource_id": "de.rampro.activitydiary.debug:id/edit_activity_name",
        "text": "Gardening",
        "view_str": "f425448d22b9eded95e32d4c297dd200_0"
      },
      "to_view": {
        "temp_id": 18,
        "class": "android.widget.EditText",
        "resource_id": "de.rampro.activitydiary.debug:id/edit_activity_name",
        "text": "HelloWorld",
        "view_str": "1e9669219eeb32fb34a2696309c4c552_0"
      }
    },
    {
      "checking_batch_id": 15,
      "from_state_str": "5f04c092f0686b332ce1c130598a0a0a",
      "to_state_str": "011da01f7d6fe08f48efd1716f14ac52",
      "from_state_id": 13,
      "to_state_id": 14,
      "from_state_json_file": "states/state_2020-03-04_060622-25.json",
      "to_state_json_file": "states/state_2020-03-04_060624-27.json",
      "annotated_utg_file": "utg_15.json",
      "operation": "INSERT",
      "from_view": null,
      "to_view": {
        "temp_id": 20,
        "class": "android.widget.FrameLayout",
        "resource_id": null,
        "text": null,
        "view_str": "bfb46681b9b809f0045502c307a22fd9_0"
      }
    }
  ]
}