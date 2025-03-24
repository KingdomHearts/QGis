from graph1 import PlotGenerator

if __name__ == "__main__":
    plot_generator = PlotGenerator(
        title="Accessibility osm106510993, 10 min wait, 6.00-24:00, transfers = 1"  # Plot title
    )
    
    # Add lines from the specified directory with specific transfer counts
    
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\106510993\\from_fix\\",        
        max_transfer = 2,
        label="from_fix",
        )
    print ("plot1")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\106510993\\to_fix\\",        
        max_transfer = 2,
        label="to_fix",
        )
    print ("plot2")
    
    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\106510993\\from_schedule\\",        
        max_transfer = 2,
        label="from_schedule",
        )
    print ("plot3")

    plot_generator.add_line(
        base_dir=r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\106510993\\to_schedule\\",        
        max_transfer = 2,
        label="to_schedule",
        )
    print ("plot4")
   
    plot_generator.save_data_to_excel(r"C:\\Users\\geosimlab\\Documents\\Igor\\experiments\\plot_data14.xlsx")

    # Generate the plot
    plot_generator.generate_plot(show_legend = True)
