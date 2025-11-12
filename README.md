# aseceza-infra
Dedicated repo for managing AWS infra and backend for my personal portfolio website.

## Goals
Should handle automatic deployment to aws lambda using OIDC, Github actions and Github secrets.

## Environment Variables
| Name | Description |
|------|--------------|
| `TOPIC_ARN` | AWS SNS topic ARN for contact form submissions |
| `RECAPTCHA_SECRET_KEY` | Google reCAPTCHA v2 secret key |


## Next: 
1. Add workflow
2. Add tests
3. Use AWS SAM
