# email_sender/templates.py

INACTIVE_TEMPLATE = {
    "subject": "We’ve missed you on 3MTT — let’s get you back on track",
    "body": """\
Hello {first_name},

We noticed you haven’t logged into your Darey.io learning dashboard in a while, and we don’t want you to fall behind on your journey. Every module you complete brings you closer to your technical goals and helps you maximise the full value of the programme.

Here are 3 quick steps to get back on track:
- Log in to your LMS here → https://3mtt.academy.darey.io/
- Continue from your last completed module
- Dedicate just 30 minutes today — progress compounds!

Your consistency matters, and we’re here to support you every step of the way. The 3MTT programme is designed for your success — let’s keep building momentum together.

[Resume Learning Now]

Keep pushing forward,

The 3MTT Support Team
""",
    "html": """\
<html>
  <body style="font-family: Arial, sans-serif; background-color: #DFFFD6; padding: 20px;">
    <div style="max-width: 600px; margin: auto; background-color: white; padding: 20px; border-radius: 8px;">
      <h2 style="color: #4CAF50;">Hello {first_name},</h2>
      <p>We noticed you haven’t logged into your Darey.io learning dashboard in a while, and we don’t want you to fall behind on your journey. Every module you complete brings you closer to your technical goals and helps you maximise the full value of the programme.</p>
      <p><strong>Here are 3 quick steps to get back on track:</strong></p>
      <ul>
        <li>Log in to your LMS here → <a href="https://3mtt.academy.darey.io/">3MTT Dashboard</a></li>
        <li>Continue from your last completed module</li>
        <li>Dedicate just 30 minutes today — progress compounds!</li>
      </ul>
      <p>Your consistency matters, and we’re here to support you every step of the way. The 3MTT programme is designed for your success — let’s keep building momentum together.</p>
      <p style="margin: 20px 0;">
        <a href="https://3mtt.academy.darey.io/" style="background-color: #A8E6A1; color: #000; padding: 10px 15px; text-decoration: none; border-radius: 5px;">Resume Learning Now</a>
      </p>
      <p style="margin-top: 20px;">Keep pushing forward,<br><strong>The 3MTT Support Team</strong></p>
    </div>
  </body>
</html>
""",
}


LOW_SCORE_TEMPLATE = {
    "subject": "Don’t stop now — boost your scores and finish strong",
    "body": """\
Hello {first_name},

You’ve been putting in effort, and we see your progress. However, your recent performance shows some modules where your scores were lower than expected. That’s absolutely okay — learning is about practice, persistence, and improvement.

Here’s how to improve your scores:
- Revisit the modules where your scores are low
- Review Knowledge Base resources for extra guidance
- Attempt practice tasks again — repetition sharpens skills

Remember, the goal is not just to complete the programme but to master the skills that will open up opportunities for you. You’ve come this far, let’s finish strong!

[Go Back to LMS and Improve Your Score]

We believe in you,

The 3MTT Support Team
""",
    "html": """\
<html>
  <body style="font-family: Arial, sans-serif; background-color: #DFFFD6; padding: 20px;">
    <div style="max-width: 600px; margin: auto; background-color: white; padding: 20px; border-radius: 8px;">
      <h2 style="color: #4CAF50;">Hello {first_name},</h2>
      <p>You’ve been putting in effort, and we see your progress. However, your recent performance shows some modules where your scores were lower than expected. That’s absolutely okay — learning is about practice, persistence, and improvement.</p>
      <p><strong>Here’s how to improve your scores:</strong></p>
      <ul>
        <li>Revisit the modules where your scores are low</li>
        <li>Review Knowledge Base resources for extra guidance</li>
        <li>Attempt practice tasks again — repetition sharpens skills</li>
      </ul>
      <p>Remember, the goal is not just to complete the programme but to master the skills that will open up opportunities for you. You’ve come this far, let’s finish strong!</p>
      <p style="margin: 20px 0;">
        <a href="https://3mtt.academy.darey.io/" style="background-color: #A8E6A1; color: #000; padding: 10px 15px; text-decoration: none; border-radius: 5px;">Go Back to LMS and Improve Your Score</a>
      </p>
      <p style="margin-top: 20px;">We believe in you,<br><strong>The 3MTT Support Team</strong></p>
    </div>


  </body>
</html>
""",
}
