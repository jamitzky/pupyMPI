make clean
PYTHONPATH=../pupympi/ make html
mv _build/html pupympi
chmod a+r pupympi
scp -r pupympi/ bromer@tyr.diku.dk:www/
ssh bromer@tyr.diku.dk chmod -R 755 www/pupympi
rm -rf pupympi
