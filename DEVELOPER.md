# Detailed Instructions of Using Genie 

## Step 0. Preparation

Create a fresh Android 6.0 emulator (Genie should be able to work on other Android versions):

```
avdmanager create avd --force --name testAVD_Android6.0 --package 'system-images;android-23;google_apis;x86' --abi google_apis/x86 --sdcard 512M --device 'Nexus 7'
```

Modify the fresh emulator for Genie (add files into sdcard and remove unnecessary default apps):

```
emulator -avd testAVD_Android6.0 &
python3 -m deploy.emulator init -s emulator-5554  # if you are not under "Genie", you should execute "cd Genie/"
```

Start the emulator in the read-only mode (without leaving any side-effect for next start-up)

```
emulator -avd testAVD_Android6.0 -read-only &
```

## Step 1. Mine GUI transitional model

```
python3 -m droidbot.start -d emulator-5554 -a apps_for_test/de.rampro.activitydiary_118.apk -policy weighted -count 2000 -grant_perm -is_emulator -interval 2 -o ./tmp-diary [-script script_samples/user_script.json]
```

Here, 

``-d``: the device serial number

``-a``: the file path of apk 

``-policy``: ``weighted`` (recommended), ``dfs_greedy``

``-count``: the maximum allowed events (we recommend ``2000`` to achieve reasonable coverage; of course, you can also set a smaller number, e.g., ``500``)

``-grant_perm``: grant all dynamic permissions while installing the apk

``-is_emulator``: declare the target device to be an emulator

``-interval``: interval in seconds between each two events (Default: 1). This option is especially used for the situation: the app has dynamic features (like the [ActivityDiary](https://github.com/functional-fuzzing-android-apps/home/tree/master/Genie/apps_for_test/de.rampro.activitydiary_118.apk) app we tested). In practice, 2 should be enough. 
If the app under test does not have dynamic features and your testing environment is stable, 0 or 1 is also okay.

**Note**: In general, we cannot ensure the app state can always reach stable during testing. Internally, Genie implements a simple workaround to check whether the app state reaches stable.

``-o``: the output directory

``-script``: the optional file path of user-defined script used for helping mining the GUI transitional model, which contains a sequence of input events (e.g., bypass welcome page, login user account). You can find some samples under ``script_samples`` (e.g., ``pass_login_script.json``, ``pass_welcome_script.json``).

## Step 2. Generate seed tests *only*

```
python3 -m droidbot.start -d emulator-5554 -a apps_for_test/de.rampro.activitydiary_118.apk -policy fuzzing_gen_seeds -count 100000 -max_seed_test_suite_size 20 -max_random_seed_test_length 15 -max_independent_trace_length 8 -max_mutants_per_insertion_position 300 -grant_perm -is_emulator -interval 1 -coverage -o ./tmp-diary [-script script_samples/user_script.json]
```

Here, 

``-policy``: ``fuzzing_gen_seeds`` (only generate seed tests)

``-count``: the maximal number of allowed events for generating seed tests (just give a large enough number, e.g., ``100000``); 

``-max_seed_test_suite_size``: the maximal number of seed tests to generate;

``-max_random_seed_test_length``: the maximal length of each seed test; 

``-max_independent_trace_length``: the maximal length of independent trace (#independent events) that is inserted into the seed test; 

``-max_mutants_per_insertion_position``: the maximal number of mutants generated for one insertion position;

``-max_mutants_per_seed_test``: the maximal number of mutants generated for one seed test;

``-coverage``: dump the coverage for seed tests (note that if you use this option, the apk needs to be  instrumented);

``-o``: the output directory used in Step 1, which is used to recover the model constructed in Step 1.

``-script``: the optional file path of user-defined script used for helping seed generation, which contains a sequence of input events (e.g., bypass welcome page, login user account). You can find some samples under ``script_samples`` (e.g., ``pass_login_script.json``, ``pass_welcome_script.json``).

**Note**: 

1. You can specify ``-max_seed_test_suite_size`` to control how many seed tests to be generated. 

2. We recommend to add ``-interval 1`` to make sure the seed generation process is stable.

3. By default, Genie adopts the ``weighted`` strategy adapted from [Stoat](https://github.com/tingsu/Stoat) to generate *diverse* random seed tests. We find the quality of seed tests is crucial for finding bugs via fuzzing.

4. In this mode, we do not need to specify ``-config-script``, which is used for oracle checking and relocate views during actual execution of mutant tests.

## Step 3. Property-preserving mutant generation and execution

For Step 3, we split it into Step 3.1 and 3.2. 

### Step 3.1: mutant generation from random seed tests (without execution of mutants)

When you already have the seed tests and you want to only generate mutant tests (but do not execute them), you can use the following command line:

```
python3 -m droidbot.start -d emulator-5554 -a apps_for_test/de.rampro.activitydiary_118.apk -policy fuzzing_gen_mutants -count 100000 -max_seed_test_suite_size 20 -max_random_seed_test_length 15 -max_independent_trace_length 8 -max_mutants_per_insertion_position 300 -grant_perm -is_emulator -interval 1 -coverage -o ./tmp-diary [-script script_samples/user_script.json]
```

Here, 

``-policy``: ``fuzzing_gen_mutants`` (generate mutant tests from the seed tests, but do not execute the mutant tests)

``-multi-mutant-gen n``: use multiprocessing when generating mutants, ``n`` is optional, default to number of seed tests

``-count``: the maximal number of allowed events for generating seed tests (just give a large enough number, e.g., ``100000``); 

``-max_seed_test_suite_size``: the maximal number of seed tests to generate;

``-max_random_seed_test_length``: the maximal length of each seed test; 

``-max_independent_trace_length``: the maximal length of independent trace (#independent events) that is inserted into the seed test; 

``-max_mutants_per_insertion_position``: the maximal number of mutants generated for one insertion position;

``-max_mutants_per_seed_test``: the maximal number of mutants generated for one seed test;

``-coverage``: dump the coverage for seed tests (note that if you use this option, the apk needs to be  instrumented);

``-o``: the output directory used in Step 1, which is used to recover the model constructed in Step 1.

``-script``: the optional file path of user-defined script used for helping seed generation, which contains a sequence of input events (e.g., bypass welcome page, login user account). You can find some samples under ``script_samples`` (e.g., ``pass_login_script.json``, ``pass_welcome_script.json``).

``-seeds-to-mutate``: the optional parameter to specify which seeds to mutate. The default value is `'all'`, which mutates all the available seed tests. 
You can also specify the specific seed tests to mutate by the ids of seed tests, e.g., `'1;2;3'` (which mutates the seed tests 1, 2, and 3).

**Note**: 

1. You can specify ``-max_seed_test_suite_size``, ``-max_random_seed_test_length``, ``-max_independent_trace_length``, ``-max_mutants_per_insertion_position`` and ``-max_mutants_per_seed_test`` to control the number of generated mutant tests. Note that the more mutants are generated, the more likely Genie can find bugs.

2. We recommend to add ``-interval 1`` to make sure the seed generation process is stable.

3. By default, Genie adopts the ``weighted`` strategy adapted from [Stoat](https://github.com/tingsu/Stoat) to generate *diverse* random seed tests. We find the quality of seed tests is crucial for finding bugs via fuzzing.

4. In this mode, we do not need to specify ``-config-script``, which is used for oracle checking and relocate views during actual execution of mutant tests.

### Comment: you can also combine seed generation and mutant generation together (without execution of mutants)

```
python3 -m droidbot.start -d emulator-5554 -a apps_for_test/de.rampro.activitydiary_118.apk -policy fuzzing_gen -count 100000 -max_seed_test_suite_size 20 -max_random_seed_test_length 15 -max_independent_trace_length 8 -max_mutants_per_insertion_position 300 -grant_perm -is_emulator -interval 1 -coverage -o ./tmp-diary [-script script_samples/user_script.json]
```

Here, 

``-policy``: ``fuzzing_gen`` (generate seed tests and their corresponding mutants, but do not execute the mutant tests)

### Step 3.2: execute mutant tests in parallel 

We currently support running mutant tests on a number of Android emulators in parallel

```
python3 -m deploy.start --avd testAVD_Android6.0 --no-headless -n 8 --apk apps_for_test/de.rampro.activitydiary_118.apk -o ./tmp-diary/ --timeout 900 --offset 2 [--script script_samples/diary_activity_ignore_view_diffs_script.json]
```

Here,

``-n N``: number of emulators/devices that will be used for distributed testing

``--offset N``: specify the starting emulator serial number. If N=1, starting from ``emulator-5556``

``--timeout``: the maximum allowed testing time allocated for each mutant test. If timeouts, we will run the mutant one more time and give up if it timeouts again.

``--script``: the optional script that specifies which views or the order of children views can be ignored when do oracle checking (this file is very important to reduce false positives).

``--no-headless``: do not hide the emulators 

Other options:

``--no-trie-reduce``: do not use trie to prune infeasible mutant tests (By default, we do not add this option. We use trie to prune infeasible mutant tests.)

``--no-trie-load``: do not load trie data from previous log (By default, we do not add this option. We use load trie data from previous run.)

``--no-skip``: do not skip any executed mutant tests (By default, we do not add this option. We will skip any executed mutant tests if we restart the fuzzing.)

``--no-coverage``: do not dump coverage of mutant tests (By default, we do not add this option. We will dump coverage for each mutant test.)

``--seeds-to-run``: ``all``, or ids of seed tests to run, like "1;2;3" (run all the mutant tests of seed tests with ids 1, 2, 3, **remember to add quotes**)

``--debug`` or ``--test-single-mutant``: the file path of a mutant (run a single mutant), this implies `--no-skip`

``--interval``: interval in seconds between each two events (Default: 0)

``--trie-delete``: delete infeasible mutants according to the trie structure during fuzzing

Note: In some cases, we may hope to rerun the mutants of some specific seeds, we can simply append ``--no-skip`` to the original command line.  But if we also add
``--no-trie-reduce``, then all the mutants will be executed again but will not use the previous trie to prune unreplayable mutants. Another way is to manually
delete the corresponding log files and rerun.

### Some useful utilities in Step 3

####(1) run one specific mutant and do oracle checking (internally called by multiple-threads fuzzing)

```
python3 -m droidbot.start -d emulator-5554 -a apps_for_test/de.rampro.activitydiary_118.apk -policy fuzzing_run -grant_perm -is_emulator -keep_app -o ./tmp-diary/ -mutant ./tmp-diary/seed-tests/seed-test-1/mutant-1 -coverage [-config-script script_samples/diary_activity_ignore_view_diffs_script.json]
```

Here,

``-policy``: ``fuzzing_run`` (run the mutant)

``-mutant``: the dir of one specified mutant (Genie will automatically infer its seed test)

``-keep_app``: keep the app after running the mutant 

``-config-script``: the optional script that specifies which views or the order of children views can be ignored when do oracle checking (this file is very important to reduce false positives). 

**Note**:
 
1. Please do not use ``-keep_env``, which may bring some issues.

2. Please use ``-keep_app``, which will not uninstall the app after running the mutant test. Before running each mutant, Genie will restore the app to its original state. So, we do not need to worry about this.

3. We may not need to specify ``-interval``.

####(2) run mutant generation and execution together in a single-thread

```
python3 -m droidbot.start -d emulator-5554 -a apps_for_test/de.rampro.activitydiary_118.apk -policy fuzzing -count 10000 -max_seed_test_suite_size 20 -max_random_seed_test_length 15 -max_independent_trace_length 8 -max_mutants_per_insertion_position 300 -grant_perm -is_emulator -interval 1 -o ./tmp-diary [-script user_script.json] [-config-script script_samples/diary_activity_ignore_view_diffs_script.json]
```

Here, 

``-policy``: fuzzing (it generates one property-preserving mutant and executes it at one time, mainly used for debugging). If we use ``fuzzing_gen``, then we only generate mutants and dump them without actual execution. This option is used for distributed testing (see below);

``-count``: the total number of events for generating seed tests (just give it a large enough number); 

``-max_seed_test_suite_size``: number of seed tests to generate;

``-max_random_seed_test_length``: the maximal length of each seed test; 

``-max_independent_trace_length``: the maximal length of independent trace that is inserted into the seed test; 

``-max_mutants_per_insertion_position``: the maximal number of mutants generated for one insertion position;

``-max_mutants_per_seed_test``: the maximal number of mutants generated for one seed test;

``-o``: specify the same directory as Phase 1, which we use to recover the model constructed in Phase 1

``-coverage``: dump the coverage for seed tests and mutant tests

``-config-script``: the optional script that specifies which views or the order of children views can be ignored when do oracle checking (this file is very important to reduce false positives).

## Step 4. Postprocess the results (reduce false positives and merge similar reported errors)


```
python3 -m droidbot.postprocess -o ./tmp-diary/ --apk apps_for_test/de.rampro.activitydiary_118.apk --check-and-merge [-f script_samples/app-ActivityDiary-script/checking_config.json] 
```

Output Report, e.g.,

``
./tmp-diary/merged_results.csv
``

The report includes:
 
 - ``#mutants`` and ``#executed_mutants``
 
 - ``crash errors`` and ``semantic errors``

We can focus on ``Crash Errors`` and ``Semantic Errors``.

## 5. Compute Jacoco-based coverage

#### Merge Coverage
`$ python3 -m deploy.coverage.merge <output-dir> --seed-cov-out <merged-seed-coverage-file-name> --mutant-cov-out <merged-mutant-coverage-file-name>`

or

`$ python3 -m deploy.coverage.merge <output-dir> --seed --mutant`, in this case `seed.ec` and `mutant.ec` will be generated under `<output-dir>`

Example (merge all coverage files of seeds and mutants):

```
python3 -m deploy.coverage.merge /mnt/droidbot-share/test-ActivityDiary-r1 --seed-cov --mutant-cov
```

Merge coverage files of specific seeds or mutants

```
python3 -m deploy.coverage.merge /mnt/droidbot-share/test-ActivityDiary-r1 --seed-cov --mutant-cov [--seeds '1;2;3'] [--mutants '1;2;3']
```

#### Get report
```$ python3 -m deploy.coverage.report --project ~/Projs/app-coverage-analysis/apps/org.jtb.alogcat_43_src-gradle --class app/build/intermediates/classes/ --source app/src/main/java/ coverage.ec[, coverages] <html-report-gen>```

Example:

```
python3 -m deploy.coverage.report --project ~/droid_repo/ActivityDiary --class app/build/intermediates/javac/debug/compileDebugJavaWithJavac/classes/ /mnt/droidbot-share/test-ActivityDiary-r1/mutant.ec /mnt/droidbot-share/test-ActivityDiary-r1-mutant-report
```

# Debugging and Verifying Genie 

To debug and verify Genie, we offer a number of debugging strategies.

#### (1) generate a number of mutants for a given seed test

This strategy can let us inspect whether Genie can indeed generate specific mutants from a given seed test. Usually, this seed test is also specified by us. 

```
python3 -m droidbot.start -d emulator-5554 -a apps_for_test/de.rampro.activitydiary_118.apk -policy fuzzing_gen -count 100000 -max_seed_test_suite_size 1 -max_random_seed_test_length 1 -max_independent_trace_length 8 -max_mutants_per_insertion_position 100 -grant_perm -is_emulator -interval 1 -coverage -script script_samples/diary_seed_test.json -o ./tmp-diary
```

**Note**:

1. We add the option ``-script script_samples/diary_seed_test.json`` so that Genie will execute this predefined seed test first before generating random seed tests.

2. We set ``-max_seed_test_suite_size 1 -max_random_seed_test_length 1`` so that Genie will only execute the given seed test and will not generate random seed tests.

3. We set ``-max_independent_trace_length 8 -max_mutants_per_insertion_position 100`` to control the mutant generation.


We provide a functionality that can show the seed test, mutant test, critical events (necessary for mutation) on the clustered utg. After successfully running the following commands, it will dump a file named ``index_clustered_utg_with_annotated_test.html`` under
the output directory, which annotates the seed test or the mutant test in red and critical views in blue.

**Note**: When a seed test was executed, the utg event ids (of the transitions of this seed test) will be updated (i.e., increased). 
Thus, when you execute a seed test and generate a number of mutant test, and want to verify the results, you should run the following
commands accordingly, so that it can reflect the change of the utg event ids.

Example usages:

#### (2) Show the seed test

Show a given seed test on the clustered utg.

```
python3 -m droidbot.debug --apk apps_for_test/instrumented_apps/org.tasks.debug-gplay-6.6.5.apk --output test-tasks-model-1/ --seed test-tasks-model-1/seed-tests/seed-test-17
```

#### (3) Show the mutant test (with its corresponding seed test)

Show a given mutant test (with its seed test) on the clustered utg.

```
python3 -m droidbot.debug --apk apps_for_test/instrumented_apps/org.tasks.debug-gplay-6.6.5.apk --output test-tasks-model-1/ --mutant test-tasks-model-1/seed-tests/seed-test-17/mutant-113/
```

#### (4) Show the seed test and highlight critical events


```
python3 -m droidbot.debug --apk apps_for_test/instrumented_apps/org.tasks.debug-gplay-6.6.5.apk --output test-tasks-model-1/ test-tasks-model-1/seed-tests/seed-test-17 --views script_samples/app-tasks-script/critical_views.json
```