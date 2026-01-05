/**
 * Test data fixtures for e2e tests
 */

export const testClientBrief = {
  companyName: 'Test Company Inc',
  businessDescription: 'We help B2B SaaS companies grow through content marketing and strategic positioning',
  idealCustomer: 'SaaS founders and marketing leaders at Series A-C companies',
  mainProblemSolved: 'Lack of consistent, high-quality content strategy and execution',
  painPoints: [
    'No time to create content consistently',
    'Struggling with content ideas that resonate',
    'Low engagement on social media posts',
  ],
  platforms: ['LinkedIn', 'Twitter'],
  tonePreference: 'Professional but approachable',
};

export const testBriefFileContent = `
Company Name: Test Company Inc
Business Description: We help B2B SaaS companies grow through content marketing
Ideal Customer: SaaS founders and marketing leaders
Main Problem Solved: Lack of consistent content strategy

Pain Points:
- No time to create content
- Struggling with content ideas
- Low engagement on social media

Platforms: LinkedIn, Twitter
Tone: Professional but approachable
`;

export const validCredentials = {
  email: 'mrskwiw@gmail.com',
  password: 'Random!1Pass',
};

export const invalidCredentials = {
  email: 'wrong@example.com',
  password: 'wrongpassword',
};

export const templateQuantities = {
  // Template ID: Quantity
  1: 3,  // Problem Recognition
  2: 2,  // Statistic + Insight
  9: 1,  // How-To
};
