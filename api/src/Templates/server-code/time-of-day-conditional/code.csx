// Return a different value based on the time of day.
var hour = DateTime.Now.Hour;

if (hour >= 22 || hour < 6) // Night time
{
    return 26.0; // Lower threshold at night
}

return 28.0; // Normal threshold during the day
