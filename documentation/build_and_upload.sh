make clean
PYTHONPATH=../pupympi/ make html
mv _build/html pupympi
scp -r pupympi/ bromer@tyr.diku.dk:www/
rm -rf pupympi
