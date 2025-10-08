# Chesanto Bakery Management System

## 1. Project Overview
### 1.1 Introduction
The Chesanto Bakery Management System is a web-based application designed to modernize and streamline the operations of Chesanto's bakery business. The system will replace the current Excel-based management system, which consists of 13 worksheets containing detailed monthly operational data. This transition aims to improve data management, reduce errors, and provide a more user-friendly interface for daily operations.

### 1.2 Project Objectives
- [ ] Migrate from Excel-based system to a centralized web-based solution
- [ ] Implement secure, role-based access control for different user types
- [ ] Automate data processing and reporting capabilities
- [ ] Reduce manual input errors through validation and proper data structuring
- [ ] Provide real-time insights into bakery operations
- [ ] Enable automated backup systems
- [ ] Create a scalable foundation for future integrations

### 1.3 Target Audience
- Bakery management staff
- Production team
- Sales and inventory staff
- Financial administrators
- Company executives (for reporting and analytics)

### 1.4 Success Criteria
- Successfully migrate all historical data from Excel workbook
- Reduce data entry time by at least 50%
- Eliminate manual calculation errors
- Achieve 100% data backup reliability
- Reduce report generation time from hours to minutes
- Positive user feedback on system usability
- Zero data loss incidents

## 2. Technical Requirements Specification

### 2.1 Backend Stack
- Django (Web Framework)
- Django REST Framework (API Development)
- SQLite (Development Database)
- PostgreSQL (Production Database)
- Python 3.x

### 2.2 Frontend Stack
- HTML5/CSS3
- Tailwind CSS (Styling)
- JavaScript (AJAX for async operations)
- [Any additional frontend libraries/frameworks needed]

### 2.3 Development Tools
- Git (Version Control)
- VS Code (IDE)
- Railway.com (Deployment Platform)

## 3. System Architecture Design

### 3.1 High-Level Architecture

The system will consist of four main components:

1. **Web Application**
   - User-friendly interface for all operations
   - Real-time data updates
   - Mobile-responsive design
   - Role-specific dashboards

2. **Business Logic Layer**
   - Automated calculations and validations
   - Business rules enforcement
   - Real-time processing
   - Data analysis and reporting

3. **Database System**
   - Centralized data storage
   - Automated backups
   - Data integrity enforcement
   - Historical data maintenance

4. **Integration Layer**
   - Mobile app connectivity
   - SMS notifications
   - Email reporting
   - Future third-party integrations

### 3.2 Component Interactions

1. **Production Management**
   - Morning stock levels trigger production planning
   - Production updates inventory automatically
   - Quality control integrated with production
   - Real-time finished goods tracking

2. **Sales Operations**
   - Territory-based sales management
   - Real-time stock availability
   - Automated returns processing
   - Instant commission calculations

3. **Financial Operations**
   - Automated banking reconciliation
   - Real-time profit calculations
   - Integrated expense tracking
   - Automated financial reporting

### 3.3 Security Considerations

1. **Access Control**
   - Role-based access system
   - Multi-factor authentication
   - Session management
   - Activity logging

2. **Data Protection**
   - Encrypted data storage
   - Secure communications
   - Regular automated backups
   - Disaster recovery plans

3. **Operational Security**
   - Transaction verification
   - Audit trails
   - Change logging
   - Error tracking

## 4. Database Schema Design

### 4.1 Data Organization

1. **Production Data**
   - Product specifications and recipes
   - Raw material inventory
   - Production batches
   - Quality control records

2. **Sales Data**
   - Customer information
   - Sales transactions
   - Returns and adjustments
   - Commission records

3. **Financial Data**
   - Daily banking records
   - Expense tracking
   - Profit calculations
   - Staff payments

### 4.2 Business Entities

1. **Products**
   - Bread (individual packets)
   - KDF (12-piece packs)
   - Scones (12-piece packs)
   - Product variations and recipes

2. **Users**
   - Management team
   - Production staff
   - Sales team
   - Support staff

3. **Operations**
   - Daily production
   - Sales and distribution
   - Quality control
   - Financial transactions

### 4.3 Data Relationships

1. **Production Chain**
   - Raw Materials → Production → Finished Goods
   - Production → Quality Control → Stock
   - Stock → Sales → Returns

2. **Financial Chain**
   - Sales → Banking → Reconciliation
   - Costs → Expenses → Profit/Loss
   - Sales → Commission → Payroll

3. **Operational Chain**
   - Stock → Territory Assignment → Sales
   - Production → Distribution → Returns
   - Orders → Delivery → Payment

## 5. API Endpoints Documentation

### 5.1 Authentication Endpoints

1. **User Management**
   ```
   POST   /api/auth/register      # New user registration
   POST   /api/auth/login         # User login
   POST   /api/auth/logout        # User logout
   PUT    /api/auth/profile       # Update user profile
   ```

2. **Access Control**
   ```
   GET    /api/auth/permissions   # Get user permissions
   POST   /api/auth/reset        # Password reset
   GET    /api/auth/verify       # Account verification
   ```

### 5.2 Core Feature Endpoints

1. **Production Operations**
   ```
   GET    /api/production/plan          # Daily production plan
   POST   /api/production/batch         # Create production batch
   PUT    /api/production/quality       # Quality control update
   GET    /api/production/inventory     # Stock levels
   ```

2. **Sales Operations**
   ```
   POST   /api/sales/order             # Create sales order
   GET    /api/sales/territory         # Territory assignments
   PUT    /api/sales/returns           # Process returns
   GET    /api/sales/commission        # Commission calculations
   ```

3. **Financial Operations**
   ```
   POST   /api/finance/banking         # Record banking
   GET    /api/finance/reconcile       # Bank reconciliation
   POST   /api/finance/expense         # Record expenses
   GET    /api/finance/profit          # Calculate profits
   ```

### 5.3 API Standards

1. **Request/Response Format**
   - JSON payload structure
   - Required fields validation
   - Error response format
   - Success response structure

2. **Authentication**
   - JWT token usage
   - Token refresh mechanism
   - Session management
   - Role-based access

3. **Status Codes**
   - 200: Successful operation
   - 201: Resource created
   - 400: Bad request
   - 401: Unauthorized
   - 403: Forbidden
   - 404: Not found
   - 500: Server error

4. **Error Handling**
   - Detailed error messages
   - Error codes
   - Validation errors
   - System errors

## 6. UI/UX Design

### 6.1 User Interface Components

1. **Dashboard Layouts**
   - Production overview
   - Sales performance metrics
   - Financial summaries
   - Quick action buttons

2. **Navigation Structure**
   - Top navigation bar
   - Side menu for main features
   - Quick access toolbar
   - Breadcrumb navigation

3. **Mobile Responsiveness**
   - Adaptive layouts
   - Touch-friendly controls
   - Simplified mobile views
   - Offline capabilities

### 6.2 User Experience Flow

1. **Production Staff**
   - Morning production planning
   - Batch tracking interface
   - Quality control forms
   - Stock management

2. **Sales Team**
   - Territory route planning
   - Order entry interface
   - Returns processing
   - Commission tracking

3. **Management**
   - Performance dashboards
   - Approval workflows
   - Report generation
   - System configuration

### 6.3 Design Standards

1. **Visual Elements**
   - Color scheme: Professional blues and whites
   - Typography: Clear, readable fonts
   - Icons: Consistent, intuitive set
   - Spacing: Clean, uncluttered layouts

2. **Interactive Elements**
   - Clear call-to-action buttons
   - Form validation feedback
   - Loading state indicators
   - Error message displays

3. **Accessibility**
   - High contrast options
   - Keyboard navigation
   - Screen reader support
   - Text size adjustment

### 6.1 Wireframes
[To be filled: Links to wireframes or descriptions]

### 6.2 User Flow
[To be filled: Description of main user journeys]

### 6.3 Design System
- Color scheme
- Typography
- Component library
- Responsive design principles

## 7. Project Timeline and Iterations

### 7.1 Phase 1: Foundation & Data Migration
- [ ] Basic project setup
- [ ] Excel workbook analysis and data mapping
- [ ] Database schema design based on Excel structure
- [ ] Data migration scripts development
- [ ] Core authentication and user roles setup
- [ ] Initial data validation rules implementation

### 7.2 Phase 2: Core Features
- [ ] Product management system (3 main products with flexibility for more)
- [ ] Inventory tracking and management
- [ ] Sales and order processing
- [ ] Automated reporting system
- [ ] Backup automation
- [ ] Basic analytics dashboard

### 7.3 Phase 3: Enhancement
- [ ] Advanced analytics and forecasting
- [ ] API development for future integrations
- [ ] Mobile responsiveness optimization
- [ ] Performance optimization
- [ ] User feedback implementation

## 8. Excel Workbook Analysis Plan

### 8.1 Initial Workbook Assessment
1. Analyze `Chesantto Books_September 2025_.xlsx`:
   - List all 13 worksheets and their purposes
   - Identify relationships between worksheets
   - Document calculation formulas and business rules
   - Map data types in each worksheet

### 8.2 Data Extraction Strategy
1. Convert worksheets to CSV format:
   - Use Python with pandas library
   - Handle multiple sheets individually
   - Preserve data types and formulas
   - Document any data cleaning required

### 8.3 Data Analysis Steps
1. For each worksheet:
   - Document column headers and their meaning
   - Identify primary keys and relationships
   - Map business processes represented
   - Note any data validation rules
   - Document calculation logic

### 8.4 Data Migration Planning
1. Create mapping documents:
   - Excel structure to database schema
   - Business rules to application logic
   - Reporting requirements
   - Data validation rules

### 8.5 Validation Strategy
1. Ensure data integrity:
   - Cross-reference totals and calculations
   - Verify relationships between sheets
   - Confirm business rule implementation
   - Test data consistency

## 9. Next Steps
1. Convert Excel worksheets to CSV format
2. Analyze worksheet structures and relationships
3. Document business rules and calculations
4. Design database schema based on findings
5. Plan data migration strategy
6. Design API endpoints and UI based on current workflows
