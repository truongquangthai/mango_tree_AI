all:
	sudo usermod -a -G dialout $(USER)
	sudo reboot
run:
	python3 physical.py
