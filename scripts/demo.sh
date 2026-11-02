#!/bin/sh
# Pays the seeded carts through the running API and checks every answer.
set -eu

api=${API_URL:-http://localhost:8000}
body=$(mktemp)
trap 'rm -f "$body"' EXIT
failures=0

token() {
    docker compose exec -T api flask issue-token "$1@example.com"
}

# check STATUS TEXT DESCRIPTION CART [TOKEN]
check() {
    status=$(curl --silent --show-error --output "$body" --write-out '%{http_code}' \
        --request POST --header "Authorization: Bearer ${5:-}" "$api/carts/$4/payments")
    if [ "$status" = "$1" ] && grep --quiet "$2" "$body"; then
        result=ok
    else
        result=FAIL
        failures=$((failures + 1))
    fi
    printf '%-4s %-40s expected %s, got %s %s\n' "$result" "$3" "$1" "$status" "$(cat "$body")"
}

alice=$(token alice)
bob=$(token bob)

check 401 unauthorized "No token" c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1
check 404 cart_not_found "Alice pays Bob's cart" c2c2c2c2-c2c2-c2c2-c2c2-c2c2c2c2c2c2 "$alice"
check 404 not_found "Malformed cart id" not-a-uuid "$alice"
check 201 '"amount":"70.00"' "Alice pays her cart" c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1 "$alice"
check 409 cart_not_active "Alice pays the same cart again" c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1 "$alice"
check 409 cart_not_active "Alice pays her abandoned cart" c6c6c6c6-c6c6-c6c6-c6c6-c6c6c6c6c6c6 "$alice"
check 402 card_declined "Bob's card is declined" c2c2c2c2-c2c2-c2c2-c2c2-c2c2c2c2c2c2 "$bob"
check 422 no_payment_method "Carol has no saved card" c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3 "$(token carol)"
check 502 provider_unavailable "Dave meets a provider outage" c4c4c4c4-c4c4-c4c4-c4c4-c4c4c4c4c4c4 "$(token dave)"
check 422 nothing_to_pay "Erin pays an empty cart" c5c5c5c5-c5c5-c5c5-c5c5-c5c5c5c5c5c5 "$(token erin)"

[ "$failures" -eq 0 ] && echo "All scenarios answered as expected." || { echo "$failures scenario(s) failed."; exit 1; }
