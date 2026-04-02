# Cognito with App Integration

## Description

#### This cognito resource integrates with the application on the frontend which hosts the UI. The app calls the cognito api via sdk and send the user credentials to cognito for verification.

## Example Usage

### How this work

- User submits credentials on your page (/login).
- Your frontend (or backend proxy) calls Cognito APIs such as:
  - InitiateAuth (for authentication)
  - SignUp / ConfirmSignUp (for registration)
  - ForgotPassword, etc.

### These endpoints live at https://cognito-idp.<region>.amazonaws.com/<userPoolId>.

- Cognito verifies credentials and returns tokens (ID, access, refresh).
- Your app stores or uses those tokens for subsequent authenticated requests.
