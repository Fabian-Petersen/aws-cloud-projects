# {
#   "Changes": [
#     {
#       "Action": "UPSERT",
#       "ResourceRecordSet": {
#         "Name": "5xdgytzrh2ndwgjphxqahvziyjsfseen._domainkey.crud-nosql.app.fabian-portfolio.net.",
#         "Type": "CNAME",
#         "TTL": 300,
#         "ResourceRecords": [
#           { "Value": "5xdgytzrh2ndwgjphxqahvziyjsfseen.dkim.amazonses.com." }
#         ]
#       }
#     },
#     {
#       "Action": "UPSERT",
#       "ResourceRecordSet": {
#         "Name": "oygitgs5eyhml2wqeaeannxxlfthi4xh._domainkey.crud-nosql.app.fabian-portfolio.net.",
#         "Type": "CNAME",
#         "TTL": 300,
#         "ResourceRecords": [
#           { "Value": "oygitgs5eyhml2wqeaeannxxlfthi4xh.dkim.amazonses.com." }
#         ]
#       }
#     },
#     {
#       "Action": "UPSERT",
#       "ResourceRecordSet": {
#         "Name": "seeg5lrz7ycw4wt3daqrihkktf4lqxj4._domainkey.crud-nosql.app.fabian-portfolio.net.",
#         "Type": "CNAME",
#         "TTL": 300,
#         "ResourceRecords": [
#           { "Value": "seeg5lrz7ycw4wt3daqrihkktf4lqxj4.dkim.amazonses.com." }
#         ]
#       }
#     }
#   ]
# }

# aws route53 change-resource-record-sets --hosted-zone-id Z093408432C9CDYPYX7VA --change-batch '{
#     "Changes": [{
#       "Action": "CREATE",
#       "ResourceRecordSet": {
#         "Name": "_amazonses.crud-nosql.app.fabian-portfolio.net.",
#         "Type": "TXT",
#         "TTL": 300,
#         "ResourceRecords": [{"Value": "\"dlKUktnhjEblfK4Uht21TjRzg77K3C3+iUbQs0Q9nEA=\""}]
#       }
#     }]
#   }'
