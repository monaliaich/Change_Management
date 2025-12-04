import os
import time
import logging
import threading
import datetime
from pathlib import Path

class Scheduler:
    """
    scheduler for periodic data extraction
    """
    def __init__(self, agent_class, data_dir="./data/input", output_dir="./data/output"):
        """
        Initialize the scheduler
        
        Args:
            agent_class: The agent class to use for extraction
            data_dir: Directory containing input data
            output_dir: Directory for output files
        """
        self.logger = logging.getLogger("SimpleScheduler")
        self.agent_class = agent_class
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.interval = 5  # Default interval in minutes
        self.running = False
        self.thread = None
        self.last_run = None
        self.next_run = None
        self.status = "idle"
    
    def set_interval(self, minutes):
        """Set the extraction interval in minutes"""
        if minutes < 1:
            self.logger.warning("Interval must be at least 1 minute")
            return False
        
        self.interval = minutes
        self.logger.info(f"Extraction interval set to {minutes} minutes")
        
        # Update next run time if scheduler is running
        if self.running:
            self._update_next_run()
        
        return True
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            self.logger.warning("Scheduler is already running")
            return False
        
        try:
            self.running = True
            self._update_next_run()
            self.status = "running"
            
            # Start the scheduler in a separate thread
            self.thread = threading.Thread(target=self._run_scheduler)
            self.thread.daemon = True
            self.thread.start()
            
            self.logger.info(f"Scheduler started with {self.interval} minute interval")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting scheduler: {str(e)}")
            self.running = False
            self.status = "error"
            return False
    
    def stop(self):
        """Stop the scheduler"""
        if not self.running:
            self.logger.warning("Scheduler is not running")
            return False
        
        try:
            self.running = False
            self.status = "stopped"
            
            # Wait for the thread to terminate
            if self.thread:
                self.thread.join(timeout=5)
            
            self.logger.info("Scheduler stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping scheduler: {str(e)}")
            return False
    
    def get_status(self):
        """Get the current scheduler status"""
        return {
            "running": self.running,
            "status": self.status,
            "interval": self.interval,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None
        }
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        self.logger.info("Scheduler thread started")
        
        while self.running:
            now = datetime.datetime.now()
            
            # Check if it's time to run the extraction
            if self.next_run and now >= self.next_run:
                self._execute_extraction()
                self._update_next_run()
            
            # Sleep for a short time to avoid high CPU usage
            time.sleep(10)
        
        self.logger.info("Scheduler thread stopped")
    
    def _update_next_run(self):
        """Update the next run time"""
        now = datetime.datetime.now()
        self.next_run = now + datetime.timedelta(minutes=self.interval)
        self.logger.info(f"Next extraction scheduled for {self.next_run}")
    
    def _execute_extraction(self):
        """Execute the extraction process"""
        start_time = datetime.datetime.now()
        self.status = "extracting"
        self.logger.info(f"Starting extraction at {start_time}")
        
        try:
            # Create agent instance
            agent = self.agent_class(data_dir=self.data_dir, output_data_dir=self.output_dir)
            
            # Run the agent
            result = agent.run()
            
            # Update status
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if result:
                output_file = agent.save_verified_population_file()
                self.logger.info(f"Extraction completed successfully in {duration:.2f} seconds")
                self.logger.info(f"Output file: {output_file}")
            else:
                self.logger.error("Extraction failed")
            
            # Update last run time
            self.last_run = start_time
            
            # Update status
            self.status = "running" if self.running else "stopped"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error during extraction: {str(e)}")
            self.status = "error"
            return False