export HOMEBREW_NO_AUTO_UPDATE=1

run:
	@networksetup -setwebproxy wi-fi 127.0.0.1 3128
	@networksetup -setsecurewebproxy wi-fi 127.0.0.1 3128
	@networksetup -setwebproxystate wi-fi on
	@networksetup -setsecurewebproxystate wi-fi on
	@bash -c "python3 -m http.server & /usr/local/opt/squid/sbin/squid -N -d 1 -f squid.conf; networksetup -setwebproxystate wi-fi off; networksetup -setsecurewebproxystate wi-fi off; killall Python"

run-err:
	@python3 -m http.server

install:
	@brew install squid
	@openssl x509 -in ssl.pem -outform DER -out ssl.der
	@sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ssl.der
	@rm ssl.der

# Win: certutil -addstore -f "ROOT" new-root-certificate.crt
# Lin: cp foo.crt /usr/local/share/ca-certificates/foo.crt

%:
	@true
