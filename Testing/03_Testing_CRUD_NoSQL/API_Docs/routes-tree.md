<!-- ctrl + shift + v to open preview on windos -->

/
├── jobs
│ ├── GET
│ ├── /request
│ │ └── POST
│ ├── /request/approved
│ │ └── POST
│ ├── /requests/rejected
│ │ └── POST
│ ├── /pending
│ │ ├── GET
│ │ └── /{jobId}
│ │ ├── GET
│ │ ├── PUT
│ │ └── DELETE
│ ├── /approved
│ │ ├── GET
│ │ └── /{jobId}
│ │ └── GET
│ ├── /execute
│ │ ├── POST
│ │ └── /{jobId}
│ │ ├── GET
│ │ ├── PUT
│ │ └── DELETE
│ └── /jobcard
│ ├── OPTIONS
│ └── /{jobId}
│ └── GET
│
├── assets
│ ├── GET
│ ├── POST
│ ├── /{assetId}
│ │ ├── GET
│ │ ├── PUT
│ │ └── DELETE
│ └── ⚠️ /{locationId} (conflicts with {assetId})
│ └── GET
│
├── users
│ ├── GET
│ ├── POST
│ ├── /get-current-user
│ │ └── GET
│ ├── /technicians
│ │ └── GET
│ ├── /contractors
│ │ └── GET
│ └── /{userId}
│ ├── GET
│ ├── PUT
│ └── DELETE
│
├── admin
│ ├── /confirm-user-signup
│ │ └── POST
│ └── /resend-temp-password
│ ├── OPTIONS
│ └── /{userId}
│ └── POST
│
└── comments
├── GET
├── POST
└── /{commentId}
└── GET
