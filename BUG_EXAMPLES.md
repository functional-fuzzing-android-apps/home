## Video illustrations of functional bugs found by Genie 
(corresponding to RQ4 in Genie's paper: Bug Types and Characteristics)

#### Bug type 1 (User data/setting lost)

This bug type leads to user data/setting lost. Sometimes, this bug type can bring severe consequences and critical user complaints.

Example Issue from [Markor](https://play.google.com/store/apps/details?id=net.gsantner.markor)

Bug report ([link](https://github.com/functional-fuzzing-android-apps/home/issues/5))


#### Bug type 2 (Function cannot proceed)

This bug type means one specific app functionality that works well before suddenly cannot proceed anymore and loses effect.

Example Issue from [SkyTube](https://skytube-app.com/)

Bug report ([link](https://github.com/functional-fuzzing-android-apps/home/issues/6))


#### Bug type 3 (Unexpected wrong behavior)

This bug type means the specific functionality shows wrong behavior w.r.t. its previous correct behavior.

Example Issue from [ActivityDiary](https://play.google.com/store/apps/details?id=de.rampro.activitydiary)

Bug report ([link](https://github.com/functional-fuzzing-android-apps/home/issues/1))


#### Bug type 4 (Inconsistent GUI states)

This bug type means the GUI states are inconsistent for specific functionality, which counters users’ intuition on app function.

Example Issue from [Transistor](https://play.google.com/store/apps/details?id=org.y20k.transistor)

Bug report ([link](https://github.com/functional-fuzzing-android-apps/home/issues/4))


#### Bug type 5-1 (Duplicated GUI views)

This bug type means some GUI views are erroneously duplicated.

Example Issue from [Tasks](https://play.google.com/store/apps/details?id=org.tasks)

Bug report ([link](https://github.com/functional-fuzzing-android-apps/home/issues/3))


#### Bug type 5-2 (Disappeared GUI views)

This bug type means some GUI views inadvertently disappear.

Example Issue from [Fosdem](https://play.google.com/store/apps/details?id=be.digitalia.fosdem)

Bug report ([link](https://github.com/functional-fuzzing-android-apps/home/issues/2))


#### Bug type 5-3 (Incorrect GUI display information)

This bug type means some views are incorrectly displayed.

Example Issue from [RadioDroid](https://play.google.com/store/apps/details?id=net.programmierecke.radiodroid2)

Bug report ([link](https://github.com/functional-fuzzing-android-apps/home/issues/9))


#### Other bug samples (much more complicated)

[UnitConverter](https://play.google.com/store/apps/details?id=com.physphil.android.unitconverterultimate) (1,000,000~50,000,000 installations on Google Play, 144 Github stars)

- User data/setting lost - bug report ([link](https://github.com/functional-fuzzing-android-apps/home/issues/7))

- This issue escaped from developer/user testing for more than 4 years.


[Markor](https://play.google.com/store/apps/details?id=net.gsantner.markor) (50,000~100,000 installations on Google Play, 1200+ Github stars)

- Inconsistent GUI states - bug report ([link](https://github.com/functional-fuzzing-android-apps/home/issues/8))

- This issue escaped from developer/user testing for more than 2.5 years and affected 74 releases.
