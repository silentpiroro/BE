# Sock Business Financial Planner

A comprehensive web application for modeling costs, pricing, and income statements for a sock manufacturing business with B2B, B2B2C, and B2C sales channels.

## Features

- **B2B Costing Model**: Calculate costs and pricing for OEM sock manufacturing with minimum order of 180 pairs
- **B2B2C Customization Model**: Pricing for customization services (printing, embroidery, woven labels) in package sizes
- **B2C Retail Model**: Calculate retail pricing and margins for packaged consumer products
- **Financial Summary**: Complete income statement with breakeven analysis
- **Visual Reports**: Charts for revenue and profit distribution across business lines
- **Data Export**: Export financial data to CSV format
- **Configuration Management**: Save and load different financial scenarios

## Business Models

### B2B OEM Development
- Minimum order of 180 pairs
- Cost components: materials, labor, overhead, packaging, shipping
- Customizable markup percentage
- Monthly order volume projection

### B2B2C Customization
- Package sizes: Small (20 pairs), Medium (60 pairs), Large (120 pairs)
- Decoration options: Printing, Embroidery, Woven Labels
- Cost components: base sock cost, decoration cost
- Individual markup percentage per package

### B2C Retail Packages
- Product types: Diabetic socks and Compression socks
- Package sizes: 3-pair and 6-pair options
- Cost components: cost per pair, packaging
- Monthly sales volume projections

## Getting Started

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/sock-business-financial-planner.git
   cd sock-business-financial-planner
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm start
   ```

4. Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

## Usage

1. **Input your data**: Enter your specific cost parameters for each business model.
2. **Navigate between tabs**: Switch between the B2B, B2B2C, and B2C tabs to view calculations for each business model.
3. **View financial summary**: See the combined financial picture in the Summary tab.
4. **Save/Load Config**: Use the buttons to save your current configuration or load a previous one.
5. **Export to CSV**: Export your income statement data for use in other tools.

## Technology Stack

- **React.js**: UI framework
- **Recharts**: Data visualization library
- **Tailwind CSS**: Utility-first CSS framework
- **Local Storage API**: For saving configurations

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
