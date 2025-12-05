curl -X 'POST' \
  'http://127.0.0.1:8080/users' \
  -H 'accept: */*' \
  -H 'Content-Type: application/json' \
  -d '{
  "username": "Kim",
  "admin": true
}' | jq


curl -X 'POST' \
  'http://127.0.0.1:8080/users' \
  -H 'accept: */*' \
  -H 'Content-Type: application/json' \
  -d '{
  "username": "Yan",
  "admin": false
}'| jq

curl -X 'POST' \
  'http://127.0.0.1:8080/users' \
  -H 'accept: */*' \
  -H 'Content-Type: application/json' \
  -d '{
  "username": "Eva",
  "admin": false
}'| jq


token=$(curl -X 'POST' \
  'http://127.0.0.1:8080/users/login' \
  -H 'accept: */*' \
  -H 'Content-Type: application/json' \
  -d '{
  "username": "Eva"
}' | jq -r .token)


curl -X 'POST' \
  'http://127.0.0.1:8080/pets' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer '"$token" \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "skippy",
  "age": 3,
  "friends": []
}'

