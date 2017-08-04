NPM_BIN = $(shell npm bin)

# Run Prettier to format all JavaScript
.PHONY: prettier
prettier:
	$(NPM_BIN)/prettier --single-quote --trailing-comma es5 --write "jeeves/**/*.js"
