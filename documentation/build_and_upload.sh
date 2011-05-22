make clean
PYTHONPATH=../pupympi/ make html
mv _build/html pupympi
chmod a+r pupympi
scp -r pupympi/ bromer@tyr.diku.dk:www/
ssh bromer@tyr.diku.dk chmod -R 755 www/pupympi
rm -rf pupympi

PYTHONPATH=../pupympi/ make latex
cd _build/latex
make all-pdf
mv pupympi.pdf ../../
cd ../../

scp pupympi.pdf bromer@tyr.diku.dk:www/pupympi/
ssh bromer@tyr.diku.dk chmod 755 www/pupympi/pupympi.pdf
