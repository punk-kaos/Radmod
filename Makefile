PYTHON ?= python3
OEM ?= stock/RT_950Pro_V0.29_260617.BTF
OUT ?= build
.PHONY: all release dev patch test clean
all: release
release:
	$(PYTHON) build.py --oem "$(OEM)" --out "$(OUT)"
dev:
	$(PYTHON) build.py --dev --oem "$(OEM)" --out "$(OUT)/dev"
patch:
	$(PYTHON) tools/patch.py "$(OEM)" "$(OUT)/radmod.patch.json" "$(OUT)/RT950_R5_RadMod_patched.BTF"
test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v
clean:
	rm -rf build

.PHONY: alpha2 alpha2-experimental
alpha2:
	$(PYTHON) build_alpha2.py --out "$(OUT)/alpha2"
alpha2-experimental:
	$(PYTHON) build_alpha2.py --target i400x1 --out "$(OUT)/alpha2-experimental"
