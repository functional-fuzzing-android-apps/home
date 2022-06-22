# This script will run the three steps at one time
# Please carefully check the parameter values, and given them appropriate values for your own use!!!
# Under Genie's main directory, and execute: source script_samples/run_genie.sh

# Command line options
# $1: emulator serial
# $2: emulator avd name
# $3: the apk path
# $4: the output dir
# $5: the ignore view script path
# E.g., source script_samples/${this_file}.sh apps_for_test/xx.apk tmp-xx/ script_samples/xx_ignore_views.json

echo "start testing"

# add -no-window if run on remote server without X-server
emulator -port 5558 -avd $2 -read-only &

echo "- Waiting for emulator to boot"
OUT=`adb -s $1 shell getprop init.svc.bootanim`
while [[ ${OUT:0:7}  != 'stopped' ]]; do
  OUT=`adb -s $1 shell getprop init.svc.bootanim`
  echo $OUT
  echo '   Waiting for emulator to fully boot...'
  sleep 5
done

echo "Emulator booted!"

# add dummpy docs
#adb -s $1 push droidbot/resources/dummy_documents/Android_logo.jpg /sdcard/
#adb -s $1 push droidbot/resources/dummy_documents/Android_robot.png /sdcard/
#adb -s $1 push droidbot/resources/dummy_documents/DroidBot_documentation.docx /sdcard/
#adb -s $1 push droidbot/resources/dummy_documents/DroidBot_documentation.pdf /sdcard/
#adb -s $1 push droidbot/resources/dummy_documents/droidbot_utg.png /sdcard/
#adb -s $1 push droidbot/resources/dummy_documents/droidmutator_test_report.png /sdcard/
#adb -s $1 push droidbot/resources/dummy_documents/password.txt /sdcard/
#adb -s $1 push droidbot/resources/dummy_documents/Heartbeat.mp3 /storage/emulated/0/Music/
#adb -s $1 push droidbot/resources/dummy_documents/intermission.mp3 /storage/emulated/0/Music/


# Step 1: model construction
echo "start model construction ..."
sleep 2
python3 -m droidbot.start -d $1 -a $3 -policy weighted -count 2000 -interval 1 -grant_perm -is_emulator -o $4 -script script_samples/transistor_pass_start_page_script.json

# back up the adb_log.txt
cp $4/logcat.txt $4/logcat.model.construction.txt

# uninstall the app (just in case the app was not successfully uninstalled in Step 1)
# adb uninstall com.bijoysingh.quicknote

# Step 2: seed and mutant generation
echo "start seed generation ..."
sleep 2

if [ ! "$5" == "" ]; then
	python3 -m droidbot.start -d $1 -a $3 -policy fuzzing_gen -count 100000 -max_seed_test_suite_size 1 -max_random_seed_test_length 1 -max_independent_trace_length 8 -max_mutants_per_insertion_position 100 -config-script $5 -interval 1 -grant_perm -is_emulator -interval 1 -coverage -o $4
else
	python3 -m droidbot.start -d $1 -a $3 -policy fuzzing_gen -count 100000 -max_seed_test_suite_size 1 -max_random_seed_test_length 1 -max_independent_trace_length 8 -max_mutants_per_insertion_position 50 -interval 1 -grant_perm -is_emulator -coverage -o $4 -script script_samples/transistor_seed_test.json
fi

# kill the emulator that constructs the model and generate seed/mutant tests; so that we can fully leverage the 16 emulators on one machine
kill -9 `ps | grep qemu-system | awk '{print $1}'`

# Step 3: distuributed fuzzing
echo "start distributed fuzzing ..."
sleep 2

if [ ! "$5" == "" ]; then
	python3 -m deploy.start -n 6 --apk $3 -o $4 --script $5 --timeout 1200 --seed-to-run "1;2;3;4;5;6;7;8;9;10"
	python3 -m deploy.start -n 6 --apk $3 -o $4 --script $5 --timeout 1200 --seed-to-run "11;12;13;14;15;16;17;18;19;20"
	python3 -m deploy.start -n 6 --apk $3 -o $4 --script $5 --timeout 1200 --seed-to-run "21;22;23;24;25;26;27;28;29;30"
	echo ""
else
	python3 -m deploy.start -n 8 --apk $3 -o $4 --timeout 1200 --offset 2
	echo ""
fi




