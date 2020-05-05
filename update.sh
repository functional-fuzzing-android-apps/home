# use this script to push to git

rm -rf .git
rm *~
rm *.log

git init
git remote add origin https://github.com/functional-fuzzing-android-apps/home.git

git config --local user.name functional-fuzzing-android-apps
git config --local user.email functional_fuzzing@163.com
git config commit.gpgsign false

git add *
git stage *
git commit -a -m "first release" --date=2020-05-05T01:00:00+0000 >> commit.log
git gc >> git-gc.log

# password!
git push --force origin HEAD
git status